"""리랭킹된 청크를 컨텍스트로 답변을 생성하고, 근거 문서 ID를 source로 반환.

관련성 판정 근거 (실측):
    코퍼스 내 질문 10개와 코퍼스 밖 질문 6개의 신호를 비교한 결과,
      - 코사인 유사도: 코퍼스 내 최저 0.660 < 코퍼스 밖 최고 0.790  → 분리 불가.
        무관한 질문이 관련 질문보다 더 높은 유사도를 받는 경우가 있어 임계값으로 못 거른다.
        (한국어 짧은 문장에서 이 임베딩 모델의 기본 유사도가 전반적으로 높게 깔리는 탓)
      - 질의어-청크 어휘 겹침: 코퍼스 내 전부 >= 1, 코퍼스 밖 전부 0  → 완전 분리.
    따라서 유사도 임계값이 아니라 어휘 겹침을 관련성 게이트로 쓴다.

    한계: 질문과 문서가 의미는 같지만 어휘가 전혀 겹치지 않으면(순수 패러프레이즈)
    관련 문서를 놓칠 수 있다. 유사도는 보조 지표로만 사용한다.

이전에 있던 "LLM이 '없다'고 답하면 템플릿으로 대체" 보정은 제거했다.
그 보정은 코퍼스 밖 질문에서 LLM의 올바른 판단을 덮어써서 무관한 문서를
"관련 문서를 찾았습니다"라고 제시하는 오답을 구조적으로 만들어냈다.
"""

from korean import terms as _terms
from llm_client import call_ollama

# 관련성 판정은 위 is_relevant() 게이트가 이미 수행했으므로(코퍼스 내 10/10, 밖 6/6 실측),
# 답변 단계에는 "관련 없으면 없다고 답하라"는 선택지를 주지 않는다.
# 그 문장을 넣어두면 gemma2:9b가 근거 조각을 받고도 "없다"로 빠져나가는 경우가 있다
# (실측: Kubernetes 장애 질문에서 해당 내용을 담은 청크가 1위로 전달됐는데도 "없음" 답변).
ANSWER_PROMPT = """\
당신은 사내 문서 검색 결과를 바탕으로 질문에 답하는 어시스턴트다.
아래 문서 조각들은 질문과 관련 있다고 이미 판정되어 선별된 것이다.
이 조각들 안에서 질문에 답할 근거를 찾아 한국어로 간결하게 답변한다.
조각에 적히지 않은 내용을 추측해서 덧붙이지는 않는다.

질문: {question}

문서 조각:
{chunks}

답변:"""

TOP_K_FOR_CONTEXT = 2    # 1위 문서 전체 + 보조 문서 최대 2개
GATE_CANDIDATES = 5      # 어휘 겹침을 확인할 상위 후보 수
MIN_SIMILARITY = 0.5     # 보조 하한선 (주 판정 기준 아님)

_DENIAL_PATTERNS = ("정보가 없", "정보는 없", "찾지 못했", "찾을 수 없", "포함되어 있지 않", "언급되어 있지 않")


def _denies_information(answer: str) -> bool:
    """생성된 답변이 '해당 정보 없음'을 말하고 있는지."""
    return any(p in answer for p in _DENIAL_PATTERNS)


def is_relevant(question: str, ranked_results: list) -> bool:
    """상위 후보 중 질의어와 어휘가 겹치는 청크가 하나라도 있는지."""
    q_terms = _terms(question)
    if not q_terms:
        return False
    for r in ranked_results[:GATE_CANDIDATES]:
        if q_terms & _terms(r["content"]):
            return True
    return False


def build_context(ranked_results: list, top_k: int = TOP_K_FOR_CONTEXT) -> list:
    """1위 문서는 전체를 넣고, 남는 자리를 다른 문서의 상위 청크로 채운다.

    청크 순위만으로 상위 K개를 자르면 두 가지 문제가 겹친다:
      · 문서마다 반복되는 정형 섹션(장애보고서의 "담당자" 등)이 흔한 단어로 겹쳐 자리를 차지한다.
      · 정작 질문이 가리키는 섹션이 유사도 상위에 못 들어 컨텍스트에서 빠진다.
    (실측: "Kubernetes 장애 대응 방법" 질문에서 조치 사항 섹션이 끝까지 누락됐다.)
    문서가 짧으므로 1위 문서는 통째로 제공한다 — parent document retrieval.
    """
    eligible = [r for r in ranked_results if r["similarity"] >= MIN_SIMILARITY]
    if not eligible:
        return []

    primary_doc = eligible[0]["doc_id"]
    try:
        from search import fetch_document_chunks

        context = fetch_document_chunks(primary_doc)
    except Exception:
        context = [r for r in eligible if r["doc_id"] == primary_doc]

    seen_docs = {primary_doc}
    for r in eligible:
        if len(seen_docs) > top_k:
            break
        if r["doc_id"] not in seen_docs:
            context.append(r)
            seen_docs.add(r["doc_id"])
    return context


def generate_answer(question: str, ranked_results: list) -> dict:
    if not ranked_results or not is_relevant(question, ranked_results):
        return {"answer": "관련 문서를 찾지 못했습니다.", "sources": []}

    context = build_context(ranked_results)
    if not context:
        return {"answer": "관련 문서를 찾지 못했습니다.", "sources": []}

    chunks_text = "\n\n".join(f"[{c['doc_id']}] {c['content']}" for c in context)
    prompt = ANSWER_PROMPT.format(question=question, chunks=chunks_text)
    answer_text = call_ollama(prompt)

    # 게이트를 통과했더라도 실제로 답이 없을 수 있다(어간 매칭이 흔한 단어로 겹친 경우).
    # 그때 LLM은 "정보가 없다"고 답하는데, 근거 문서 목록만 그대로 붙으면
    # "출처는 있는데 답은 없다"는 모순된 결과가 된다. 답변이 부재를 말하면 인용도 비운다.
    # 주의: 답변 내용을 바꾸지 않고 인용만 맞춘다 (LLM의 판단을 덮어쓰지 않는다).
    if _denies_information(answer_text):
        return {"answer": "관련 문서를 찾지 못했습니다.", "sources": []}

    sources = sorted({c["doc_id"] for c in context})
    return {"answer": answer_text, "sources": sources}


if __name__ == "__main__":
    from rerank import rerank
    from search import search_chunks

    for q in ["SSL 인증서 관련 장애가 있었어?", "회사 주차장 이용 규정 알려줘"]:
        ranked = rerank(q, search_chunks(q, top_k=100))
        out = generate_answer(q, ranked)
        print(f"\n질문: {q}\n  답변: {out['answer'][:100]}\n  근거: {out['sources']}")
