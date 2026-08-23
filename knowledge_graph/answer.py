"""그래프 순회 결과를 자연어 답변으로 변환."""

from llm_client import call_ollama

ANSWER_PROMPT = """\
당신은 지식 그래프 탐색 결과를 자연스러운 한국어 문장으로 요약하는 어시스턴트다.
아래 "탐색 결과 목록"은 질문에 대한 정답 그 자체다 (그래프에서 질문의 조건에 맞게 이미 찾아낸 노드들이다).
이 목록에 있는 이름들을 그대로 사용해서 질문에 답한다. 목록 밖의 내용을 추측해서 덧붙이지 않는다.
목록이 비어 있을 때만 "관련된 결과를 찾지 못했습니다"라고 답한다. 목록에 항목이 하나라도 있으면
반드시 그 항목들을 이용해 답변을 작성해야 한다 ("정보 없음"이라고 답하면 안 된다).

질문: {question}

탐색 결과 목록 ({count}건):
{nodes}

답변:"""


def _format_node(n: dict) -> str:
    label = n.get("name", n.get("id", "?"))
    extra = {k: v for k, v in n.items() if k not in ("name", "id", "type")}
    extra_text = ", ".join(f"{k}={v}" for k, v in extra.items())
    return f"- {label} ({n.get('type', '')}{': ' + extra_text if extra_text else ''})"


_NEGATIVE_PATTERNS = ["없습니다", "없음", "없다", "포함되어 있지 않", "찾지 못했"]


def _template_answer(nodes: list) -> str:
    """결과 노드가 있는데 LLM이 '없음'으로 잘못 답할 때 쓰는 결정론적 폴백."""
    names = [n.get("name", n.get("id", "?")) for n in nodes]
    return f"관련 결과 {len(nodes)}건: " + ", ".join(names)


def generate_answer(question: str, traverse_result: dict) -> str:
    if traverse_result.get("error"):
        return traverse_result["error"]

    nodes = traverse_result.get("nodes", [])
    if not nodes:
        return "관련된 결과를 찾지 못했습니다."

    preview = nodes[:30]
    nodes_text = "\n".join(_format_node(n) for n in preview)
    if len(nodes) > 30:
        nodes_text += f"\n... 외 {len(nodes) - 30}개 생략"

    prompt = ANSWER_PROMPT.format(question=question, nodes=nodes_text, count=len(nodes))
    llm_answer = call_ollama(prompt)

    # 결과 노드가 분명히 있는데 LLM이 "없다"고 말하면 신뢰하지 않고 템플릿으로 대체한다
    # (작은 로컬 모델이 노드 목록에 질문 키워드가 그대로 없으면 없다고 오판하는 현상 실측됨)
    if any(p in llm_answer for p in _NEGATIVE_PATTERNS):
        return _template_answer(nodes)

    return llm_answer


if __name__ == "__main__":
    sample = {"nodes": [{"type": "product", "name": "Product-S1"}, {"type": "product", "name": "Product-C3"}]}
    print(generate_answer("Client-A가 사용 중인 제품 목록은?", sample))
