"""Step 2: 문서 타입 추정 + 키워드 매칭 가중치로 벡터 검색 결과를 재정렬한다."""

import re

TYPE_KEYWORDS = {
    "incident_report": ["장애", "오류", "다운", "타임아웃", "에러"],
    "technical_doc": ["설치", "가이드", "매뉴얼", "레퍼런스", "튜닝", "아키텍처", "API", "방법", "백업", "정책", "운영"],
    "meeting_note": ["회의", "미팅", "점검", "논의", "일정"],
    "proposal": ["제안", "도입"],
}

SIMILARITY_WEIGHT = 1.0
# 임베딩이 짧은 한글 보일러플레이트 문장에 편향되는 현상이 있어(예: "백업" 정확 매칭 청크보다
# 무관한 "담당자" 섹션이 더 높은 코사인 유사도를 받음), 키워드 정확 매칭 가중치를 similarity 오차 범위보다
# 크게 잡는다.
KEYWORD_WEIGHT = 0.08
TYPE_MATCH_BONUS = 0.05


def _infer_query_type(query: str) -> str | None:
    scores = {t: sum(1 for kw in kws if kw in query) for t, kws in TYPE_KEYWORDS.items()}
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else None


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[가-힣A-Za-z0-9]+", text))


def rerank(query: str, results: list[dict]) -> list[dict]:
    query_type = _infer_query_type(query)
    query_terms = _tokenize(query)

    for r in results:
        content_terms = _tokenize(r["content"])
        keyword_overlap = len(query_terms & content_terms)
        type_bonus = TYPE_MATCH_BONUS if query_type and r["metadata"].get("type") == query_type else 0.0
        r["rerank_score"] = (
            SIMILARITY_WEIGHT * r["similarity"] + KEYWORD_WEIGHT * keyword_overlap + type_bonus
        )

    return sorted(results, key=lambda r: r["rerank_score"], reverse=True)


if __name__ == "__main__":
    from search import search_chunks

    query = "SSL 인증서 관련 장애가 있었어?"
    results = search_chunks(query, top_k=8)
    ranked = rerank(query, results)
    for r in ranked:
        print(f"[sim={r['similarity']:.3f} rerank={r['rerank_score']:.3f}] {r['doc_id']} ({r['metadata']['type']})")
