"""벡터 검색 엔드투엔드 파이프라인: 질문 -> 검색 -> 리랭킹 -> 답변."""

from answer import generate_answer
from rerank import rerank
from search import search_chunks


def answer_question(question: str, top_k: int = 100) -> dict:
    # 코퍼스가 작을 때(수백 청크 이하)는 1차 후보군을 넉넉히 가져와야 재순위 로직이
    # 효과가 있다 — 좁은 top_k로는 정답 청크가 애초에 후보에 안 들어가는 문제가 실측됨.
    results = search_chunks(question, top_k=top_k)
    ranked = rerank(question, results)
    out = generate_answer(question, ranked)

    return {
        "answer": out["answer"],
        "raw_data": ranked,
        "tool": "vector_search",
        "source": out["sources"],
    }


if __name__ == "__main__":
    out = answer_question("백업 정책은 어떻게 되어 있어?")
    print("ANSWER:", out["answer"])
    print("SOURCE:", out["source"])
