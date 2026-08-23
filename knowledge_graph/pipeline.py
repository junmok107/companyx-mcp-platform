"""지식 그래프 엔드투엔드 파이프라인: 질문 -> 스펙 추출 -> 그래프 순회 -> 자연어 답변."""

from answer import generate_answer
from extract import extract_spec
from loader import build_name_index, load_graph
from traverse import execute

_graph = None
_name_index = None


def _get_graph():
    global _graph, _name_index
    if _graph is None:
        _graph = load_graph()
        _name_index = build_name_index(_graph)
    return _graph, _name_index


def answer_question(question: str) -> dict:
    g, name_index = _get_graph()
    try:
        spec = extract_spec(question)
    except Exception as e:
        return {"answer": f"질문을 그래프 스펙으로 변환하지 못했습니다: {e}", "raw_data": None, "source": "knowledge_graph"}

    result = execute(g, spec, name_index)
    answer_text = generate_answer(question, result)
    return {"answer": answer_text, "raw_data": result, "source": "knowledge_graph", "spec": spec}


if __name__ == "__main__":
    out = answer_question("클라우드사업부 소속 직원들은 누구야?")
    print("SPEC:", out["spec"])
    print("ANSWER:", out["answer"])
