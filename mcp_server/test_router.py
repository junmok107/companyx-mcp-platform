"""questions.json 30문항 전체로 라우터 정확도를 검증한다."""

import json
from pathlib import Path

from router import route

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "questions.json"


def main():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    correct = 0
    for q in questions:
        predicted = route(q["q"])
        ok = predicted == q["tool"]
        correct += ok
        mark = "OK  " if ok else "FAIL"
        print(f"{mark} [{q['tool']:>15} -> {predicted:>15}] {q['q']}")

    print(f"\n정확도: {correct}/{len(questions)} ({correct/len(questions)*100:.0f}%)")


if __name__ == "__main__":
    main()
