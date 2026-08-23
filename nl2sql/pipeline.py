"""NL2SQL 엔드투엔드 파이프라인: 질문 → SQL 생성 → 실행 → 자연어 답변.

라우터 연동 규격에 맞춰 { answer, raw_data, source } 형식으로 반환한다.
"""

import re

from answer import generate_answer
from executor import UnsafeQueryError, run_select
from llm_client import call_ollama
from prompt import build_nl2sql_prompt

# "가장 많은 ~는?" 류 질문에서 공동 1위를 살리기 위한 후처리용 패턴.
# 프롬프트에 RANK()를 쓰라는 규칙을 넣어도 gemma2:9b가 자주 무시하고 LIMIT 1을 생성하므로
# (실측), 프롬프트에 의존하지 않고 결과 단계에서 동점을 확인한다.
SUPERLATIVE_PATTERN = re.compile(r"가장|최다|최대|최고|최소|제일|공동\s*1위|동점")
LIMIT_ONE_PATTERN = re.compile(r"\bLIMIT\s+1\s*$", re.IGNORECASE)
ORDER_BY_PATTERN = re.compile(r"ORDER\s+BY\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE)
# ORDER BY 뒤의 정렬식 전체. 상관 서브쿼리처럼 컬럼명이 아닌 식도 잡는다.
# LIMIT 절은 있어도 되고 없어도 된다.
ORDER_BY_EXPR_PATTERN = re.compile(
    r"\bORDER\s+BY\s+(.+?)(?:\s+(?:ASC|DESC))?(?:\s+LIMIT\s+\d+)?\s*$", re.IGNORECASE | re.DOTALL)
ANY_LIMIT_PATTERN = re.compile(r"\s*\bLIMIT\s+\d+\s*$", re.IGNORECASE)
# "공동 1위만 알려줘"처럼 동점 상위만 요구하는 질문 (전체 목록 요구와 구분해야 한다)
TOP_GROUP_ONLY_PATTERN = re.compile(r"공동\s*1위|동점|1위인")
TIE_SCAN_LIMIT = 50
TIE_KEY = "__tiekey"


def _expand_ties(question: str, sql: str, result: dict) -> dict:
    """LIMIT 1로 잘린 1위 질의에 공동 1위가 있으면 모두 되살린다.

    아래 조건을 하나라도 만족하지 못하면 원본 결과를 그대로 반환한다(fail-closed):
    질문이 1위를 묻지 않음 / 결과가 1행이 아님 / SQL이 LIMIT 1로 끝나지 않음 /
    ORDER BY 기준 컬럼을 결과 컬럼에서 못 찾음 / 확장 질의 실행 실패.
    """
    if not SUPERLATIVE_PATTERN.search(question) or result["row_count"] != 1:
        return result

    trimmed = sql.strip().rstrip(";").strip()
    if not LIMIT_ONE_PATTERN.search(trimmed):
        return result

    order_match = ORDER_BY_PATTERN.search(trimmed)
    order_col = order_match.group(1).split(".")[-1] if order_match else None

    if order_col and order_col in result["columns"]:
        # 정렬 기준이 결과 컬럼에 그대로 있는 경우 — 그 컬럼으로 동점을 판정한다.
        widened_sql = LIMIT_ONE_PATTERN.sub(f"LIMIT {TIE_SCAN_LIMIT}", trimmed)
        col_index = result["columns"].index(order_col)
        drop_key = False
    else:
        # 정렬 기준이 상관 서브쿼리 등 '식'이라 결과에 없는 경우.
        # 그 식을 SELECT 목록에 별칭으로 덧붙여 값을 꺼내온다. 서브쿼리로 감싸면 바깥 테이블
        # 별칭이 보이지 않아 실패하므로, 원본 질의의 SELECT 목록에 직접 끼워 넣는다.
        widened_sql = _inject_tiekey(trimmed)
        if widened_sql is None:
            return result
        col_index = -1
        drop_key = True

    try:
        widened = run_select(widened_sql)
    except Exception:
        return result

    if not widened["rows"]:
        return result
    if drop_key and widened["columns"][-1] != TIE_KEY:
        return result

    top_value = widened["rows"][0][col_index]
    tied = [r for r in widened["rows"] if r[col_index] == top_value]
    if len(tied) <= 1:
        return result

    columns, rows = widened["columns"], tied
    if drop_key:  # 내부용 정렬키 컬럼은 사용자에게 보여주지 않는다
        columns = columns[:-1]
        rows = [r[:-1] for r in tied]
    return {"columns": columns, "rows": rows, "row_count": len(rows),
            "total_count": len(rows), "truncated": False}


def _top_level_from_index(sql: str) -> int | None:
    """괄호 밖(최상위)에 있는 첫 FROM의 위치. 서브쿼리 안의 FROM은 건너뛴다."""
    depth = 0
    for m in re.finditer(r"\(|\)|\bFROM\b", sql, re.IGNORECASE):
        token = m.group(0)
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif depth == 0:
            return m.start()
    return None


def _inject_tiekey(sql: str) -> str | None:
    """`SELECT ... FROM ...` 의 SELECT 목록에 정렬식을 __tiekey 별칭으로 추가하고 LIMIT을 넓힌다."""
    expr_match = ORDER_BY_EXPR_PATTERN.search(sql)
    if not expr_match:
        return None
    expr = expr_match.group(1).strip()
    if not expr or expr.upper().startswith(("ASC", "DESC")):
        return None

    from_at = _top_level_from_index(sql)
    if from_at is None or not sql[:from_at].strip().upper().startswith("SELECT"):
        return None

    injected = f"{sql[:from_at].rstrip()}, ({expr}) AS {TIE_KEY} {sql[from_at:]}"
    if ANY_LIMIT_PATTERN.search(injected):
        return ANY_LIMIT_PATTERN.sub(f" LIMIT {TIE_SCAN_LIMIT}", injected)
    return f"{injected} LIMIT {TIE_SCAN_LIMIT}"


def _restrict_to_top_group(question: str, sql: str, result: dict) -> dict:
    """"공동 1위만" 요구한 질문에 전체 목록이 돌아온 경우 1위 그룹만 남긴다.

    프롬프트에 RANK()를 쓰라는 규칙을 넣어도 모델이 정렬만 하고 전체를 반환하는 일이 있다
    (실측: "공동 1위로 프로젝트를 가장 많이 가진 고객사를 모두" → 22개 고객사 전부 반환).
    질문이 1위 그룹만 요구했는데 결과가 여러 건이면, 정렬 기준값이 1위와 같은 행만 남긴다.
    """
    if not TOP_GROUP_ONLY_PATTERN.search(question) or result["row_count"] <= 1:
        return result

    trimmed = sql.strip().rstrip(";").strip()
    if not re.search(r"\bORDER\s+BY\b", trimmed, re.IGNORECASE):
        return result

    order_match = ORDER_BY_PATTERN.search(trimmed)
    order_col = order_match.group(1).split(".")[-1] if order_match else None

    if order_col and order_col in result["columns"]:
        idx = result["columns"].index(order_col)
        top = result["rows"][0][idx]
        tied = [r for r in result["rows"] if r[idx] == top]
        columns, rows = result["columns"], tied
    else:
        widened_sql = _inject_tiekey(trimmed)
        if widened_sql is None:
            return result
        try:
            widened = run_select(widened_sql)
        except Exception:
            return result
        if not widened["rows"] or widened["columns"][-1] != TIE_KEY:
            return result
        top = widened["rows"][0][-1]
        tied = [r for r in widened["rows"] if r[-1] == top]
        columns, rows = widened["columns"][:-1], [r[:-1] for r in tied]

    if len(rows) >= result["row_count"]:
        return result
    return {"columns": columns, "rows": rows, "row_count": len(rows),
            "total_count": len(rows), "truncated": False}


def _clean_sql(text: str) -> str:
    """LLM이 규칙을 어기고 마크다운 코드펜스를 붙이는 경우를 방어적으로 제거한다."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # 첫 줄의 ```sql 제거
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_sql(question: str) -> str:
    p = build_nl2sql_prompt(question)
    full_prompt = f"{p['system']}\n\n{p['user']}"
    raw = call_ollama(full_prompt)
    return _clean_sql(raw)


def _explain_db_error(exc: Exception) -> str:
    """DB 오류를 사용자용 메시지로 바꾼다.

    존재하지 않는 컬럼/테이블을 참조하는 SQL이 생성되는 경우는 대개 질문이 요구하는 정보가
    데이터에 없다는 뜻이다. 원문 오류(예: column "blood_type" does not exist)를 그대로
    보여주면 사용자에게 도움이 안 되고 스키마 정보만 흘러나간다. 원문은 error 필드에 남긴다.
    """
    name = type(exc).__name__
    if name in ("UndefinedColumn", "UndefinedTable", "UndefinedFunction"):
        return "질문하신 내용에 해당하는 데이터가 이 데이터베이스에 없습니다."
    if name == "QueryCanceled":
        return "조회 시간이 너무 오래 걸려 중단했습니다. 조건을 좁혀서 다시 물어봐 주세요."
    return "조회를 처리하지 못했습니다. 질문을 조금 더 구체적으로 바꿔서 다시 시도해 주세요."


REPAIR_PROMPT = """\
아래 SQL이 PostgreSQL에서 오류로 실패했다. 오류 메시지를 보고 고친 SQL을 하나만 반환한다.
설명 없이 SQL만 출력한다. SELECT 문이어야 하며 스키마에 없는 컬럼/별칭을 쓰지 않는다.

질문: {question}
실패한 SQL: {sql}
오류: {error}

수정한 SQL:"""


def _repair_sql(question: str, sql: str, error: str) -> str | None:
    """실행 오류를 되먹여 한 번만 다시 생성한다.

    모델이 존재하지 않는 별칭을 참조하는 SQL을 만드는 경우가 있다
    (실측: "직원 수가 가장 적은 부서는?" -> ORDER BY COUNT(e.id) 인데 JOIN이 없음).
    특정 질문에 맞춘 few-shot을 늘리는 대신, 오류 메시지를 근거로 한 번 고쳐 쓰게 한다.
    """
    p = build_nl2sql_prompt(question)
    prompt = p["system"] + "\n\n" + REPAIR_PROMPT.format(question=question, sql=sql, error=error)
    try:
        return _clean_sql(call_ollama(prompt))
    except Exception:
        return None


def answer_question(question: str) -> dict:
    sql = generate_sql(question)
    try:
        result = run_select(sql)
    except UnsafeQueryError as e:
        return {"answer": f"안전하지 않은 쿼리라 실행을 거부했습니다: {e}", "raw_data": None,
                "tool": "nl2sql", "source": [], "sql": sql}
    except Exception as e:
        repaired = _repair_sql(question, sql, f"{type(e).__name__}: {e}")
        if repaired and repaired != sql:
            try:
                result = run_select(repaired)
                sql = repaired
            except Exception as e2:
                return {"answer": _explain_db_error(e2), "raw_data": None, "tool": "nl2sql",
                        "source": [], "sql": repaired, "error": f"{type(e2).__name__}: {e2}"}
        else:
            return {"answer": _explain_db_error(e), "raw_data": None, "tool": "nl2sql",
                    "source": [], "sql": sql, "error": f"{type(e).__name__}: {e}"}

    result = _expand_ties(question, sql, result)
    result = _restrict_to_top_group(question, sql, result)
    answer_text = generate_answer(question, result)
    # source는 세 도구 공통으로 '근거 목록'이다 (NL2SQL의 근거는 실행된 쿼리).
    return {"answer": answer_text, "raw_data": result, "tool": "nl2sql",
            "source": [" ".join(sql.split())], "sql": sql}


if __name__ == "__main__":
    out = answer_question("현재 활성 상태인 계약 수는 몇 개야?")
    print("SQL:", out["sql"])
    print("ANSWER:", out["answer"])
