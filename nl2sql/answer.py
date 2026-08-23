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

ANSWER_PROMPT = """\
당신은 질문에 대한 데이터 조회 결과를 자연스러운 한국어 문장으로 요약하는 어시스턴트다.
아래 질문과 SQL 조회 결과를 보고, 결과에 있는 사실만 근거로 한 문장으로 간결하게 답변한다.
결과에 없는 내용을 추측해서 덧붙이지 않는다.

질문: {question}

조회 결과 (컬럼: {columns}):
{rows}

답변:"""


def _format_row(columns: list, row: tuple) -> str:
    if len(columns) == 1:
        return str(row[0])
    return ", ".join(f"{c}={v}" for c, v in zip(columns, row))


def render_rows(columns: list, rows: list) -> str:
    """조회 결과를 누락 없이 결정론적으로 문자열로 만든다."""
    shown = rows[:MAX_DISPLAY_ROWS]
    lines = [f"- {_format_row(columns, r)}" for r in shown]
    header = f"총 {len(rows)}건:"
    if len(rows) > MAX_DISPLAY_ROWS:
        lines.append(f"- ... 외 {len(rows) - MAX_DISPLAY_ROWS}건")
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

    return render_rows(columns, rows)


if __name__ == "__main__":
    multi = {
        "columns": ["name", "total_sales"],
        "rows": [("Client-Q", 23244), ("Client-Y", 22865), ("Client-I", 10898), ("Client-A", 10707)],
        "row_count": 4,
    }
    print("[다중 행 — 결정론적 렌더링]")
    print(generate_answer("서울 지역 매출 상위 5개 고객사를 알려줘", multi))

    single = {"columns": ["count"], "rows": [(46,)], "row_count": 1}
    print("\n[단일 값 — LLM 문장화]")
    print(generate_answer("현재 활성 상태인 계약 수는 몇 개야?", single))
