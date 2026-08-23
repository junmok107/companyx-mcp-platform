"""SQL 실행 결과를 자연어 답변으로 변환.

Ollama 로컬 서버(기본 http://localhost:11434)에 붙어 질문 + 쿼리 결과를
한국어 답변으로 요약한다. 팀원의 Ollama 연동 모듈이 준비되면 OLLAMA_MODEL,
OLLAMA_HOST를 그쪽과 통일하면 된다.
"""

from llm_client import call_ollama

ANSWER_PROMPT = """\
당신은 질문에 대한 데이터 조회 결과를 자연스러운 한국어 문장으로 요약하는 어시스턴트다.
아래 질문과 SQL 조회 결과를 보고, 결과에 있는 사실만 근거로 간결하게 답변한다.
결과에 없는 내용을 추측해서 덧붙이지 않는다. 행이 0개면 "조회된 결과가 없습니다"라고 답한다.

질문: {question}

조회 결과 (컬럼: {columns}):
{rows}

답변:"""


def generate_answer(question: str, query_result: dict) -> str:
    """query_result: executor.run_select()가 반환하는 {columns, rows, row_count} 형식."""
    columns = query_result["columns"]
    rows = query_result["rows"]

    if not rows:
        return "조회된 결과가 없습니다."

    # 결과가 너무 많으면 LLM 프롬프트가 비대해지므로 상위 20행만 전달
    rows_preview = rows[:20]
    rows_text = "\n".join(str(r) for r in rows_preview)
    if len(rows) > 20:
        rows_text += f"\n... 외 {len(rows) - 20}행 생략"

    prompt = ANSWER_PROMPT.format(question=question, columns=columns, rows=rows_text)
    return call_ollama(prompt)


if __name__ == "__main__":
    sample_result = {
        "columns": ["name", "total_sales"],
        "rows": [("Client-Q", 23244), ("Client-Y", 22865), ("Client-I", 10898), ("Client-A", 10707)],
        "row_count": 4,
    }
    answer = generate_answer("서울 지역 매출 상위 5개 고객사를 알려줘", sample_result)
    print(answer)
