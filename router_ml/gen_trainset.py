"""LLM 증류 1단계 — 교사 LLM으로 학습용 질문을 대량 생성한다.

각 도구의 정의와 소수 예시를 주고, 다양한 문체·표현의 새 질문을 생성시킨다.
생성된 질문은 곧바로 라벨(생성 시 지정한 도구)을 갖는다.
추가로 gen_labels.py가 교사 LLM으로 교차 검증 라벨링을 한다.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nl2sql"))
from llm_client import call_ollama  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "trainset.jsonl"

TOOL_SPECS = {
    "nl2sql": (
        "정형 데이터베이스(매출, 계약, 직원, 제품, 고객사, 프로젝트, 티켓 테이블)에서 "
        "수치를 집계하거나 조건으로 걸러 답하는 질문. 예: 합계, 평균, 개수, 최대/최소, 순위, 필터.",
        ["서울 지역 매출 상위 5개 고객사", "활성 계약이 몇 건이야", "평균 연봉이 가장 높은 부서"],
    ),
    "knowledge_graph": (
        "고객사-제품-직원-부서-프로젝트 사이의 '관계'를 탐색해 답하는 질문. "
        "예: 누가 무엇을 사용/담당/소속/리드하는가, 관계 개수 순위.",
        ["Client-A가 사용하는 제품", "경영지원팀 팀장은 누구", "가장 많은 고객을 담당하는 직원"],
    ),
    "vector_search": (
        "장애보고서·기술문서·회의록·제안서 등 '문서에 서술된 내용'을 찾아 답하는 질문. "
        "예: 장애 원인, 설치 방법, 정책, 회의 논의 내용, 제안 효과.",
        ["최근 서버 장애 원인", "제품 설치 방법", "백업 정책이 어떻게 돼"],
    ),
}

GEN_PROMPT = """\
당신은 한국어 질문 데이터셋 생성기다. 아래 도구에 해당하는 질문을 {n}개 생성한다.

[도구: {tool}]
{spec}

기존 예시(참고용, 그대로 베끼지 말 것):
{examples}

생성 규칙:
- 문체를 최대한 다양하게: 존댓말/반말/구어체/공식체.
- 표현을 다양하게: 동의어, 조사 변화, 띄어쓰기 변화, 영어 혼용, 간접 표현, 긴 질문/짧은 질문.
- 엔티티 이름은 Client-A~Client-Z, Product-C1 등 또는 부서명(영업팀 등)을 자유롭게 사용.
- 반드시 위 도구의 성격에 정확히 맞는 질문만 생성한다.
- 한 줄에 질문 하나씩. 번호나 불릿 없이 질문 문장만 출력한다.
"""


def generate_for_tool(tool: str, spec, examples, n: int, rounds: int) -> list[str]:
    questions = set()
    for r in range(rounds):
        prompt = GEN_PROMPT.format(
            n=n, tool=tool, spec=spec,
            examples="\n".join(f"- {e}" for e in examples),
        )
        # temperature를 올려 다양성 확보 (라벨은 도구가 고정이므로 다양성이 이득)
        raw = call_ollama(prompt, temperature=0.9, timeout=120)
        for line in raw.splitlines():
            q = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
            if 4 <= len(q) <= 80 and q.endswith(("?", "요", "줘", "어", "야", "까", "지", "래", "게", "다", ".")):
                questions.add(q)
        print(f"  [{tool}] round {r+1}/{rounds}: 누적 {len(questions)}개")
    return sorted(questions)


def main():
    n_per_round = 25
    rounds = 6  # 도구당 최대 150개 시도 → 중복 제거 후 대략 80~120개
    all_rows = []
    for tool, (spec, examples) in TOOL_SPECS.items():
        qs = generate_for_tool(tool, spec, examples, n_per_round, rounds)
        for q in qs:
            all_rows.append({"question": q, "label": tool})
        print(f"  => {tool}: 최종 {len(qs)}개")

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n총 {len(all_rows)}개 질문을 {OUT_PATH}에 저장")


if __name__ == "__main__":
    main()
