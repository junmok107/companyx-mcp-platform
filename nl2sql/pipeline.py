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
SUPERLATIVE_PATTERN = re.compile(r"가장|최다|최대|최고|최소|제일")
LIMIT_ONE_PATTERN = re.compile(r"\bLIMIT\s+1\s*$", re.IGNORECASE)
ORDER_BY_PATTERN = re.compile(r"ORDER\s+BY\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE)
TIE_SCAN_LIMIT = 50


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
    if not order_match:
        return result
    order_col = order_match.group(1).split(".")[-1]
    if order_col not in result["columns"]:
        return result
    col_index = result["columns"].index(order_col)

    try:
        widened = run_select(LIMIT_ONE_PATTERN.sub(f"LIMIT {TIE_SCAN_LIMIT}", trimmed))
    except Exception:
        return result

    if not widened["rows"]:
        return result
    top_value = widened["rows"][0][col_index]
    tied = [r for r in widened["rows"] if r[col_index] == top_value]
    if len(tied) <= 1:
        return result
    return {"columns": widened["columns"], "rows": tied, "row_count": len(tied)}


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


def answer_question(question: str) -> dict:
    sql = generate_sql(question)
    try:
        result = run_select(sql)
    except UnsafeQueryError as e:
        return {"answer": f"안전하지 않은 쿼리라 실행을 거부했습니다: {e}", "raw_data": None, "source": "nl2sql", "sql": sql}
    except Exception as e:
        return {"answer": f"쿼리 실행 중 오류가 발생했습니다: {e}", "raw_data": None, "source": "nl2sql", "sql": sql}

    result = _expand_ties(question, sql, result)
    answer_text = generate_answer(question, result)
    return {"answer": answer_text, "raw_data": result, "source": "nl2sql", "sql": sql}


if __name__ == "__main__":
    out = answer_question("현재 활성 상태인 계약 수는 몇 개야?")
    print("SQL:", out["sql"])
    print("ANSWER:", out["answer"])
