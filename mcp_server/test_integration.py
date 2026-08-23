"""questions.json 30문항 전체를 server.ask()로 실행하는 통합 테스트.

라우터가 올바른 도구를 선택했는지 + 실제 답변까지 한 번에 확인한다.
"""

import json
from pathlib import Path

import server

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "questions.json"


def main():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    routing_correct = 0
    results = []

    for i, q in enumerate(questions, 1):
        out = server.ask(q["q"])
        routed_ok = out["routed_to"] == q["tool"]
        routing_correct += routed_ok
        print(f"\n[{i}/{len(questions)}] ({'OK' if routed_ok else 'MISROUTE'}) {q['q']}")
        print(f"    기대 도구: {q['tool']} / 라우팅: {out['routed_to']}")
        print(f"    답변: {out['answer'][:150]}")
        results.append({
            "question": q["q"],
            "expected_tool": q["tool"],
            "routed_to": out["routed_to"],
            "answer": out["answer"],
        })

    print(f"\n라우팅 정확도: {routing_correct}/{len(questions)} ({routing_correct/len(questions)*100:.0f}%)")

    out_path = Path(__file__).resolve().parent / "integration_test_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"결과 저장: {out_path}")


if __name__ == "__main__":
    main()
