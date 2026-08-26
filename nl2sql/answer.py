"""SQL 실행 결과를 자연어 답변으로 변환.

설계 근거 — 목록형 결과는 LLM에 요약시키지 않는다:
    소형 로컬 모델(gemma2:9b)에 여러 행을 주고 요약을 시키면 일부 행을 조용히 누락한다.
    실측: "Critical 미해결 티켓" 질문에서 SQL은 5행을 정확히 반환했으나 답변은 5회 반복
    실행 모두 1건만 언급했다(재현되는 결정론적 누락). 조회 결과를 빠짐없이 전달하는 것이
    이 도구의 핵심 가치이므로, 행이 2개 이상이면 LLM을 거치지 않고 결정론적으로 렌더링한다.
    부수 효과로 LLM 호출 1회가 줄어 응답 시간도 짧아진다.
"""

from decimal import Decimal

from llm_client import call_ollama

MAX_DISPLAY_ROWS = 50


def _is_number(v) -> bool:
    # PostgreSQL의 AVG/SUM 등은 numeric → psycopg가 Decimal로 돌려준다. int/float만 보면
    # 집계 금액이 통째로 포맷에서 빠져(F-1) 원시값이 LLM에 넘어가 100배 틀린 단위가 붙는다.
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)

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

# 다열(3열 이상) 결과를 사람이 읽기 좋게 다듬기 위한 컬럼 라벨/값 사전.
# raw_data 원본은 그대로 두고, 화면에 보이는 answer 문장만 한글 라벨·축약값으로 바꾼다.
COL_LABELS = {
    "id": "번호", "name": "이름", "title": "제목", "email": "이메일",
    "contact_email": "담당자이메일", "position": "직급", "dept": "부서",
    "dept_name": "부서", "department": "부서", "hire_date": "입사일",
    "salary": "연봉", "industry": "업종", "region": "지역", "company_size": "규모",
    "contact_name": "담당자", "registered_at": "등록일", "category": "카테고리",
    "description": "설명", "price_monthly": "월요금", "version": "버전",
    "release_date": "출시일", "status": "상태", "contract_type": "계약유형",
    "amount": "금액", "start_date": "시작일", "end_date": "종료일", "budget": "예산",
    "sale_date": "매출일", "quarter": "분기", "priority": "우선순위",
    "created_at": "등록일", "resolved_at": "해결일", "count": "건수",
}
# 알려진 enum 컬럼의 값만 한글로 옮긴다(다른 컬럼의 같은 문자열을 건드리지 않게 컬럼명으로 한정).
ENUM_MAPS = {
    "status": {"active": "활성", "completed": "완료", "cancelled": "취소",
               "planning": "계획", "in_progress": "진행중", "on_hold": "보류",
               "open": "미해결", "resolved": "해결", "closed": "종료", "beta": "베타"},
    "priority": {"low": "낮음", "medium": "보통", "high": "높음", "critical": "긴급"},
}

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


def _humanize_label(col) -> str:
    return COL_LABELS.get(str(col).lower(), str(col).replace("_", " "))


def _is_id_col(col) -> bool:
    c = str(col).lower()
    return c == "id" or c.endswith("_id") or c.endswith("_no") or c.endswith("code")


def _is_name_col(col) -> bool:
    c = str(col).lower()
    return c in ("name", "title") or c.endswith("_name")


def _format_value(col, v) -> str:
    """값 하나를 사람이 읽기 좋게 변환: 금액→억/만원, enum→한글, 일시→날짜, 불리언→예/아니오."""
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if _is_money_col(col) and _is_number(v):
        return format_manwon(v)
    s = str(v)
    c = str(col).lower()
    if c in ENUM_MAPS and s in ENUM_MAPS[c]:
        return ENUM_MAPS[c][s]
    # 'YYYY-MM-DD ...' 형태의 날짜/일시는 날짜만 남긴다(분기 '2025-Q3'는 길이가 짧아 제외).
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    if len(s) > 80:
        return s[:79] + "…"
    return s


def _format_row_multi(columns: list, row: tuple) -> str:
    """3열 이상: 이름/제목을 앞세우고 #번호를 붙인 뒤, 나머지는 '라벨 값 · 라벨 값'으로."""
    pairs = list(zip(columns, row))
    used: set[int] = set()
    lead = ""
    head_idx = next((i for i, (c, _) in enumerate(pairs) if _is_name_col(c)), None)
    if head_idx is None:  # 이름/제목 컬럼이 없으면 첫 비ID 문자열 컬럼을 머리로 쓴다.
        head_idx = next((i for i, (c, v) in enumerate(pairs)
                         if not _is_id_col(c) and isinstance(v, str)), None)
    if head_idx is not None:
        lead = _format_value(*pairs[head_idx])
        used.add(head_idx)
        id_idx = next((i for i, (c, _) in enumerate(pairs) if _is_id_col(c)), None)
        if id_idx is not None:
            lead = f"#{pairs[id_idx][1]} {lead}"
            used.add(id_idx)
    rest = [f"{_humanize_label(c)} {_format_value(c, v)}"
            for i, (c, v) in enumerate(pairs) if i not in used]
    segs = ([lead] if lead else []) + rest
    return " · ".join(segs)


def _format_row(columns: list, row: tuple) -> str:
    if len(columns) == 1:
        return _format_value(columns[0], row[0])
    # (개체, 지표) 2열은 가장 흔한 목록 형태다. "이름 — 값"으로 자연스럽게 읽히게 한다.
    if len(columns) == 2:
        return f"{_format_value(columns[0], row[0])} — {_format_value(columns[1], row[1])}"
    return _format_row_multi(columns, row)


def _sum_summary(columns: list, rows: list) -> str:
    """가산 가능한 금액 컬럼이 정확히 하나면 합계 한 줄을 만든다. 아니면 빈 문자열."""
    idxs = [i for i, c in enumerate(columns) if _is_additive_money_col(c)]
    if len(idxs) != 1:
        return ""
    i = idxs[0]
    try:
        total = sum(r[i] for r in rows if _is_number(r[i]))
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


# 별칭 없는 집계(round(avg(amount)) 등)는 컬럼명이 'round'라 금액으로 인식되지 않는다.
# 단일값 경로에서 질문이 금액을 묻는데 결과가 숫자면 만원 단위로 포맷해 LLM에 넘긴다(F-1 보완).
_MONEY_NOUNS = ("금액", "매출액", "매출", "연봉", "예산", "계약금", "단가", "비용", "가격", "요금")
_MONEY_AGG_CTX = ("얼마", "평균", "총", "합계", "최대", "최소", "최고", "최저", "큰", "작은", "높", "낮")


def _is_money_question(question: str) -> bool:
    return any(n in question for n in _MONEY_NOUNS) and any(c in question for c in _MONEY_AGG_CTX)


_COUNT_HINTS = ("몇 개", "몇개", "몇 건", "몇건", "개수", "건수", "몇 명", "몇명", "인원", "수는", "수야", "건이")


def _is_count_question(question: str) -> bool:
    return any(h in question for h in _COUNT_HINTS)


def generate_answer(question: str, query_result: dict) -> str:
    """query_result: executor.run_select()가 반환하는 {columns, rows, row_count} 형식."""
    columns = query_result["columns"]
    rows = query_result["rows"]

    if not rows:
        return "조회된 결과가 없습니다."

    # 단일 행·단일 값(집계 결과 등)만 LLM으로 자연스럽게 문장화한다. 누락 위험이 없고
    # "총 매출액은 23859입니다" 같은 답변이 목록 형태보다 읽기 좋기 때문.
    if len(rows) == 1 and len(columns) == 1:
        col, val = columns[0], rows[0][0]
        # 건수 질문의 0은 LLM이 비문("계약은 건이 없어요")을 만들기 쉬워 결정론적으로 답한다(F-3).
        if isinstance(val, int) and not isinstance(val, bool) and val == 0 and _is_count_question(question):
            return "조건에 해당하는 건이 없습니다 (0건)."
        if _is_number(val) and (_is_money_col(col) or _is_money_question(question)):
            shown = format_manwon(val)
        else:
            shown = _format_value(col, val)
        prompt = ANSWER_PROMPT.format(question=question, columns=columns, rows=shown)
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
    print("\n[3열 — 이름 머리 + 한글 라벨 + 금액 포맷]")
    print(render_rows(emp["columns"], emp["rows"], emp["total_count"], emp["truncated"]))

    tickets = {
        "columns": ["id", "title", "status", "created_at"],
        "rows": [(37, "프로덕션 핫픽스 요청", "in_progress", "2026-03-20 16:08:23"),
                 (64, "디스크 용량 부족 경고", "open", "2025-04-15 11:32:44")],
        "total_count": 2, "truncated": False,
    }
    print("\n[4열 — #번호 + 제목 머리 + 상태/날짜 한글화·축약]")
    print(render_rows(tickets["columns"], tickets["rows"], tickets["total_count"], tickets["truncated"]))

    count = {"columns": ["count"], "rows": [(5,)]}
    print("\n[비금액 단일값 — 그대로]")
    print(_format_row(count["columns"], count["rows"][0]))
