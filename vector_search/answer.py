"""Step 3: 리랭킹된 청크를 컨텍스트로 답변을 생성하고, 근거 문서 ID를 source로 반환."""

from llm_client import call_ollama

ANSWER_PROMPT = """\
당신은 사내 문서 검색 결과를 바탕으로 질문에 답하는 어시스턴트다.
아래 문서 조각들만 근거로 답변한다. 조각에 없는 내용을 추측해서 덧붙이지 않는다.
관련 내용이 전혀 없으면 "관련 문서를 찾지 못했습니다"라고 답한다.

질문: {question}

문서 조각:
{chunks}

답변:"""

TOP_K_FOR_CONTEXT = 3
SIMILARITY_THRESHOLD = 0.5  # 이보다 낮으면 답변 컨텍스트에서 제외 (무관한 문서 노출 방지)
_NEGATIVE_PATTERNS = ["없습니다", "없음", "없다", "찾지 못했", "찾을 수 없"]


def build_context(ranked_results: list[dict], top_k: int = TOP_K_FOR_CONTEXT) -> list[dict]:
    return [r for r in ranked_results if r["similarity"] >= SIMILARITY_THRESHOLD][:top_k]


def _template_answer(context: list[dict]) -> str:
    """컨텍스트가 있는데 LLM이 '없음'으로 오판할 때 쓰는 결정론적 폴백 (지식그래프 도구와 동일 패턴)."""
    parts = [f"[{c['doc_id']}] {c['content'][:200]}" for c in context]
    return "관련 문서를 찾았습니다:\n" + "\n\n".join(parts)


def generate_answer(question: str, ranked_results: list[dict]) -> dict:
    context = build_context(ranked_results)
    if not context:
        return {"answer": "관련 문서를 찾지 못했습니다.", "sources": []}

    chunks_text = "\n\n".join(f"[{c['doc_id']}] {c['content']}" for c in context)
    prompt = ANSWER_PROMPT.format(question=question, chunks=chunks_text)
    answer_text = call_ollama(prompt)

    # 컨텍스트가 분명히 있는데 LLM이 "없다"고 하면 신뢰하지 않고 템플릿으로 대체
    if any(p in answer_text for p in _NEGATIVE_PATTERNS):
        answer_text = _template_answer(context)

    sources = sorted({c["doc_id"] for c in context})
    return {"answer": answer_text, "sources": sources}


if __name__ == "__main__":
    from rerank import rerank
    from search import search_chunks

    q = "SSL 인증서 관련 장애가 있었어?"
    ranked = rerank(q, search_chunks(q, top_k=8))
    out = generate_answer(q, ranked)
    print("ANSWER:", out["answer"])
    print("SOURCES:", out["sources"])
