"""그래프 순회 결과를 자연어 답변으로 변환.

설계 근거 — 목록형 결과는 LLM에 요약시키지 않는다 (nl2sql/answer.py와 동일한 이유):
    실측: "진행 중인 프로젝트를 이끄는 직원" 질문에서 그래프 순회는 11명을 정확히 찾았으나
    LLM 요약 답변은 5회 반복 실행 모두 9명만 언급했다(강현우·류서연 고정 누락).
    이전에는 "결과가 있는데 LLM이 없다고 하면 템플릿으로 대체"하는 사후 보정을 뒀는데,
    그 방식은 코퍼스에 없는 질문에서 LLM의 올바른 "없음" 판단까지 덮어써 오답을 만들었다.
    따라서 보정 대신, 목록은 애초에 LLM을 거치지 않도록 구조를 바꿨다.
"""

from llm_client import call_ollama

MAX_DISPLAY_NODES = 50

ANSWER_PROMPT = """\
당신은 지식 그래프 탐색 결과를 자연스러운 한국어 문장으로 요약하는 어시스턴트다.
아래 질문과 탐색 결과를 보고, 결과에 있는 사실만 근거로 한 문장으로 간결하게 답변한다.
결과에 없는 내용을 추측해서 덧붙이지 않는다.

질문: {question}

탐색 결과: {node}

답변:"""


def _label(n: dict) -> str:
    return n.get("name", n.get("id", "?"))


def _describe(n: dict) -> str:
    label = _label(n)
    extra = {k: v for k, v in n.items() if k not in ("name", "id", "type")}
    if not extra:
        return label
    return f"{label} ({', '.join(f'{k}={v}' for k, v in extra.items())})"


def render_nodes(nodes: list) -> str:
    """탐색 결과를 누락 없이 결정론적으로 문자열로 만든다."""
    shown = nodes[:MAX_DISPLAY_NODES]
    lines = [f"- {_describe(n)}" for n in shown]
    if len(nodes) > MAX_DISPLAY_NODES:
        lines.append(f"- ... 외 {len(nodes) - MAX_DISPLAY_NODES}건")
    return f"총 {len(nodes)}건:\n" + "\n".join(lines)


def generate_answer(question: str, traverse_result: dict) -> str:
    if traverse_result.get("error"):
        return traverse_result["error"]

    nodes = traverse_result.get("nodes", [])
    if not nodes:
        return "관련된 결과를 찾지 못했습니다."

    # 단일 결과(부서장, 최다 집계 1건 등)만 LLM으로 문장화한다 — 누락 위험이 없다.
    if len(nodes) == 1:
        prompt = ANSWER_PROMPT.format(question=question, node=_describe(nodes[0]))
        return call_ollama(prompt)

    return render_nodes(nodes)


if __name__ == "__main__":
    multi = {"nodes": [{"type": "product", "name": "Product-S1"}, {"type": "product", "name": "Product-C3"}]}
    print("[다중 결과 — 결정론적 렌더링]")
    print(generate_answer("Client-A가 사용 중인 제품 목록은?", multi))

    single = {"nodes": [{"type": "employee", "name": "윤소연", "position": "부장"}]}
    print("\n[단일 결과 — LLM 문장화]")
    print(generate_answer("경영지원팀 팀장은 누구야?", single))
