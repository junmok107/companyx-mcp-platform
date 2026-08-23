"""questions.json의 nl2sql 카테고리 10문항을 파이프라인으로 실행하고 결과를 출력한다."""

import json
from pathlib import Path

from pipeline import answer_question

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "questions.json"


def main():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    nl2sql_questions = [q for q in questions if q["tool"] == "nl2sql"]

    results = []
    for i, q in enumerate(nl2sql_questions, 1):
        print(f"\n[{i}/{len(nl2sql_questions)}] 질문: {q['q']}")
        print(f"    힌트: {q['hint']}")
        out = answer_question(q["q"])
        sql_one_line = " ".join(out["sql"].split())
        print(f"    생성 SQL: {sql_one_line}")
        print(f"    답변: {out['answer']}")
        results.append({"question": q["q"], "hint": q["hint"], "sql": out["sql"], "answer": out["answer"]})

    out_path = Path(__file__).resolve().parent / "nl2sql_test_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 {len(results)}건을 {out_path}에 저장했습니다. hint와 대조해서 수동으로 정답 여부를 판정하세요.")


if __name__ == "__main__":
    main()
