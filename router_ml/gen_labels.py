"""LLM 증류 2단계 — 교사 LLM으로 재라벨링하고 노이즈를 걸러낸다.

생성 시 지정한 라벨을 그대로 믿지 않는다(LLM이 엉뚱한 질문을 만들기도 함).
각 질문을 교사 LLM으로 라벨링해, 생성 라벨과 교사 라벨이 일치하는 질문만 남긴다.
이렇게 '교사가 확신하는' 깨끗한 학습셋을 만든다.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nl2sql"))
from llm_client import call_ollama  # noqa: E402

IN_PATH = Path(__file__).resolve().parent / "trainset.jsonl"
OUT_PATH = Path(__file__).resolve().parent / "trainset_clean.jsonl"

TOOLS = ("nl2sql", "knowledge_graph", "vector_search")

LABEL_PROMPT = """\
다음 질문을 처리할 도구를 하나만 고른다.

nl2sql: 매출·계약·연봉·가격·건수 등 수치를 집계하거나 조건으로 거르는 질문
knowledge_graph: 고객사-제품-직원-부서-프로젝트 사이의 관계(사용, 담당, 소속, 리드)를 묻는 질문
vector_search: 장애보고서·기술문서·회의록·제안서에 서술된 내용을 묻는 질문

도구 이름 하나만 출력한다. 다른 말은 쓰지 않는다.

질문: {q}
도구:"""


def teacher_label(q: str) -> str | None:
    ans = call_ollama(LABEL_PROMPT.format(q=q), temperature=0.0, timeout=60).strip().lower()
    for t in TOOLS:
        if t in ans:
            return t
    return None


def main():
    rows = [json.loads(l) for l in IN_PATH.open(encoding="utf-8")]
    kept, dropped = [], []
    for i, row in enumerate(rows):
        tl = teacher_label(row["question"])
        # 생성 라벨과 교사 라벨이 일치할 때만 채택 (교사가 확신하는 깨끗한 예시)
        if tl is not None and tl == row["label"]:
            kept.append({"question": row["question"], "label": tl})
        else:
            dropped.append({"question": row["question"], "gen": row["label"], "teacher": tl})
        if (i + 1) % 50 == 0:
            print(f"  라벨링 {i+1}/{len(rows)}  유지 {len(kept)} 탈락 {len(dropped)}")

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"\n최종 유지 {len(kept)}/{len(rows)}  (탈락 {len(dropped)})")
    print("유지 라벨 분포:", dict(Counter(r["label"] for r in kept)))
    print("\n탈락 샘플 (생성라벨 != 교사라벨):")
    for d in dropped[:12]:
        print(f"  gen={d['gen']:<16} teacher={str(d['teacher']):<16} | {d['question']}")


if __name__ == "__main__":
    main()
