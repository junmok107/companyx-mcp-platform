"""Step 2: 문서 타입 추정 + 키워드 매칭 가중치로 벡터 검색 결과를 재정렬한다."""

import math

from korean import terms as _tokenize

# 최상단에서 import한다. mcp_server/bridge는 도구 로드 후 각 도구 디렉터리를 sys.path에서
# 제거하므로, 함수 안에서 지연 import하면 실행 시점에 경로가 없어 실패한다(IDF가 조용히 꺼짐).
# 로드 시점(경로가 살아 있을 때) 참조를 묶어 둔다.
try:
    from search import corpus_doc_frequencies
except Exception:  # pragma: no cover - search가 아직 로드 안 된 특수 상황
    corpus_doc_frequencies = None

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
# 나아가 겹치는 단어를 개수로만 세면 흔한 단어(장애·부족)만 겹쳐도 정형 문구 공유 문서가 상위를
# 차지한다(F-5). 그래서 IDF로 가중해, 특정 문서에만 있는 변별 어휘(컨테이너·OOM 등)의 매칭을
# 흔한 어휘보다 크게 반영한다.
KEYWORD_WEIGHT = 0.08
TYPE_MATCH_BONUS = 0.05


def _infer_query_type(query: str) -> str | None:
    scores = {t: sum(1 for kw in kws if kw in query) for t, kws in TYPE_KEYWORDS.items()}
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else None


def _idf(term: str, df: dict, n: int) -> float:
    # 흔할수록 0에 가깝고, 희소할수록 커진다. df+1 스무딩, 음수는 0으로 절단.
    return max(0.0, math.log(n / (df.get(term, 0) + 1)))


def rerank(query: str, results: list[dict]) -> list[dict]:
    query_type = _infer_query_type(query)
    query_terms = _tokenize(query)

    try:
        df, n = corpus_doc_frequencies() if corpus_doc_frequencies else ({}, 0)
    except Exception:
        df, n = {}, 0  # 코퍼스 통계를 못 구하면 IDF=1로 폴백(개수 세기와 동일 거동)

    for r in results:
        content_terms = _tokenize(r["content"])
        overlap = query_terms & content_terms
        # IDF 합. 코퍼스 통계가 없으면 개수(각 1.0)로 되돌린다.
        keyword_score = sum(_idf(t, df, n) for t in overlap) if n else float(len(overlap))
        type_bonus = TYPE_MATCH_BONUS if query_type and r["metadata"].get("type") == query_type else 0.0
        r["rerank_score"] = (
            SIMILARITY_WEIGHT * r["similarity"] + KEYWORD_WEIGHT * keyword_score + type_bonus
        )

    return sorted(results, key=lambda r: r["rerank_score"], reverse=True)


if __name__ == "__main__":
    from search import search_chunks

    query = "SSL 인증서 관련 장애가 있었어?"
    results = search_chunks(query, top_k=8)
    ranked = rerank(query, results)
    for r in ranked:
        print(f"[sim={r['similarity']:.3f} rerank={r['rerank_score']:.3f}] {r['doc_id']} ({r['metadata']['type']})")
