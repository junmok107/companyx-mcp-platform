"""SQL 실행 결과를 자연어 답변으로 변환.

설계 근거 — 목록형 결과는 LLM에 요약시키지 않는다:
    소형 로컬 모델(gemma2:9b)에 여러 행을 주고 요약을 시키면 일부 행을 조용히 누락한다.
    실측: "Critical 미해결 티켓" 질문에서 SQL은 5행을 정확히 반환했으나 답변은 5회 반복
    실행 모두 1건만 언급했다(재현되는 결정론적 누락). 조회 결과를 빠짐없이 전달하는 것이
    이 도구의 핵심 가치이므로, 행이 2개 이상이면 LLM을 거치지 않고 결정론적으로 렌더링한다.
    부수 효과로 LLM 호출 1회가 줄어 응답 시간도 짧아진다.
"""

from llm_client import call_ollama

MAX_DISPLAY_ROWS = 50

# ── 금액 포맷 ──
# 모든 금액 컬럼(salary, price_monthly, amount, budget)과 그 집계 별칭(total_sales,
# avg_salary 등)은 만원 단위 정수다(schema_context.md). raw 숫자를 그대로 찍으면
# "total_sales=23244"처럼 단위 없이 읽기 어려우므로, 만원 단위를 억/만원으로 환산해 보여준다.
# (finance-mcp의 formatBillions 아이디어를 우리 데이터 단위(만원)에 맞게 이식.)
MONEY_TOKENS = ("salary", "price", "amount", "budget", "sales", "revenue",
                "매출", "금액", "연봉", "가격", "예산")
# 이름에 아래 토큰이 있으면 금액이 아니다(건수·비율·연도 등). 오탐을 막는 차단 목록.
NON_MONEY_TOKENS = ("count", "cnt", "_id", "num", "rate", "ratio", "pct",
                    "percent", "개수", "건수", "비율", "age", "year", "month",
                    "date", "quarter", "_no")
# 합산이 의미 있는 금액 컬럼(총액·매출 등)만 요약에 합계를 낸다. 평균·증가율은 제외.
ADDITIVE_TOKENS = ("total", "sum", "amount", "sales", "매출", "금액", "합계")
NON_ADDITIVE_TOKENS = ("avg", "mean", "평균", "증가율", "rate", "ratio")

ANSWER_PROMPT = """\
당신은 질문에 대한 데이터 조회 결과를 자연스러운 한국어 문장으로 요약하는 어시스턴트다.
아래 질문과 SQL 조회 결과를 보고, 결과에 있는 사실만 근거로 한 문장으로 간결하게 답변한다.
결과에 없는 내용을 추측해서 덧붙이지 않는다. 금액이 '억/만원' 형태로 주어지면 그 표기를 그대로 쓴다.

질문: {question}

조회 결과 (컬럼: {columns}):
{rows}

답변:"""


def _has_token(col, tokens) -> bool:
    c = str(col).lower()
    return any(t in c for t in tokens)


def _is_money_col(col) -> bool:
    return not _has_token(col, NON_MONEY_TOKENS) and _has_token(col, MONEY_TOKENS)


def _is_additive_money_col(col) -> bool:
    return _is_money_col(col) and not _has_token(col, NON_ADDITIVE_TOKENS) \
        and _has_token(col, ADDITIVE_TOKENS)


def format_manwon(value) -> str:
    """만원 단위 숫자를 사람이 읽기 좋은 억/만원 표기로 변환. (23244 → '2억 3,244만원')"""
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    neg = val < 0
    a = abs(val)
    eok, man = divmod(a, 10000)
    eok = int(eok)
    if eok >= 1:
        if man == 0:
            s = f"{eok:,}억원"
        elif float(man).is_integer():
            s = f"{eok:,}억 {int(man):,}만원"
        else:
            s = f"{eok:,}억 {man:,.1f}만원"
    elif float(a).is_integer():
        s = f"{int(a):,}만원"
    else:
        s = f"{a:,.1f}만원"
    return ("-" + s) if neg else s


def _format_value(col, v):
    if isinstance(v, bool):
        return str(v)
    if _is_money_col(col) and isinstance(v, (int, float)):
        return format_manwon(v)
    return str(v)


def _format_row(columns: list, row: tuple) -> str:
    if len(columns) == 1:
        return _format_value(columns[0], row[0])
    # (개체, 지표) 2열은 가장 흔한 목록 형태다. "이름 — 값"으로 자연스럽게 읽히게 한다.
    if len(columns) == 2:
        return f"{_format_value(columns[0], row[0])} — {_format_value(columns[1], row[1])}"
    # 3열 이상은 어떤 값인지 구분이 필요하므로 컬럼명을 유지하되 값은 포맷한다.
    return ", ".join(f"{c}={_format_value(c, v)}" for c, v in zip(columns, row))


def _sum_summary(columns: list, rows: list) -> str:
    """가산 가능한 금액 컬럼이 정확히 하나면 합계 한 줄을 만든다. 아니면 빈 문자열."""
    idxs = [i for i, c in enumerate(columns) if _is_additive_money_col(c)]
    if len(idxs) != 1:
        return ""
    i = idxs[0]
    try:
        total = sum(r[i] for r in rows if isinstance(r[i], (int, float)) and not isinstance(r[i], bool))
    except (TypeError, ValueError, IndexError):
        return ""
    return f" · 합계 {format_manwon(total)}"


def render_rows(columns: list, rows: list, total: int | None = None, truncated: bool = False) -> str:
    """조회 결과를 누락 없이 결정론적으로 문자열로 만든다.

    total은 실행기가 알려준 실제 총 행 수다. 표시 상한이나 조회 상한에 걸렸다면
    가져온 행 수가 아니라 실제 총계를 밝히고, 몇 건만 보여주는지 명시한다.
    """
    shown = rows[:MAX_DISPLAY_ROWS]
    lines = [f"- {_format_row(columns, r)}" for r in shown]

    if total is None:
        header = f"조회된 결과가 많아 총 건수를 확인하지 못했습니다. 아래 {len(shown)}건만 표시합니다:"
    elif total > len(shown):
        note = " (조회 상한에 걸려 일부만 가져옴)" if truncated else ""
        header = f"총 {total}건 중 {len(shown)}건 표시{note}:"
    else:
        # 전체 행을 빠짐없이 가져온 경우에만 합계 요약을 붙인다(부분 집계는 오해를 부른다).
        header = f"총 {total}건{_sum_summary(columns, rows)}:"
    return header + "\n" + "\n".join(lines)


def generate_answer(question: str, query_result: dict) -> str:
    """query_result: executor.run_select()가 반환하는 {columns, rows, row_count} 형식."""
    columns = query_result["columns"]
    rows = query_result["rows"]

    if not rows:
        return "조회된 결과가 없습니다."

    # 단일 행·단일 값(집계 결과 등)만 LLM으로 자연스럽게 문장화한다. 누락 위험이 없고
    # "총 매출액은 23859입니다" 같은 답변이 목록 형태보다 읽기 좋기 때문.
    if len(rows) == 1 and len(columns) == 1:
        prompt = ANSWER_PROMPT.format(question=question, columns=columns, rows=_format_row(columns, rows[0]))
        return call_ollama(prompt)

    return render_rows(columns, rows, query_result.get("total_count", len(rows)),
                       query_result.get("truncated", False))


if __name__ == "__main__":
    multi = {
        "columns": ["name", "total_sales"],
        "rows": [("Client-Q", 23244), ("Client-Y", 22865), ("Client-I", 10898), ("Client-A", 10707)],
        "row_count": 4, "total_count": 4, "truncated": False,
    }
    print("[다중 행 — 결정론적 렌더링 + 금액 포맷 + 합계]")
    print(render_rows(multi["columns"], multi["rows"], multi["total_count"], multi["truncated"]))

    dept = {
        "columns": ["dept", "avg_salary"],
        "rows": [("경영지원팀", 7213.5), ("기술지원팀", 5480.0)],
        "total_count": 2, "truncated": False,
    }
    print("\n[평균 금액 — 억/만원 환산, 합계는 붙이지 않음]")
    print(render_rows(dept["columns"], dept["rows"], dept["total_count"], dept["truncated"]))

    emp = {
        "columns": ["name", "dept", "salary"],
        "rows": [("홍길동", "기술지원팀", 5200), ("김철수", "기술지원팀", 4800)],
        "total_count": 2, "truncated": False,
    }
    print("\n[3열 — 컬럼명 유지, 금액만 포맷]")
    print(render_rows(emp["columns"], emp["rows"], emp["total_count"], emp["truncated"]))

    count = {"columns": ["count"], "rows": [(5,)]}
    print("\n[비금액 단일값 — 그대로]")
    print(_format_row(count["columns"], count["rows"][0]))
