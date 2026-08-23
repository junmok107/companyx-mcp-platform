"""라우터 정확도 회귀 테스트.

세 개의 세트로 나눠 측정한다. 튜닝에 쓴 세트의 점수는 일반화 성능의 근거가 되지 못하므로
반드시 구분해서 봐야 한다.

  TUNED     questions.json 30문항 — 라우터 키워드를 이 세트를 보며 맞췄다 (과적합 전제)
  HOLDOUT   1차 held-out 18문항 — 처음엔 15/18(83%)이었고, 그 실패를 근거로 설계를 고쳤다.
            즉 이 세트도 이제는 튜닝에 쓰인 세트다.
  FRESH     2차 held-out 15문항 — 설계 수정 이후에 작성했고 튜닝에 쓰지 않았다.
            현재 시점에서 일반화 성능을 대표하는 유일한 숫자.

새로 튜닝할 때마다 FRESH를 다음 세트로 승격하고 새 FRESH를 만들어야 의미가 유지된다.
"""

import json
from pathlib import Path

from router import DEFAULT_TOOL, route, route_by_rules, score_tools

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "questions.json"

HOLDOUT = [
    ("부산 지역 고객사는 몇 개야?", "nl2sql"),
    ("2026년 1분기 매출 합계 알려줘", "nl2sql"),
    ("계약 금액이 가장 큰 계약 5건은?", "nl2sql"),
    ("직원 평균 연봉은 얼마야?", "nl2sql"),
    ("제품별 가격을 비싼 순으로 보여줘", "nl2sql"),
    ("미해결 티켓이 몇 건이야?", "nl2sql"),
    ("제품 업데이트 배포 전략이 문서에 어떻게 적혀 있어?", "vector_search"),
    ("로그 수집은 어떻게 관리해?", "vector_search"),
    ("모니터링 지표는 뭘 보나요?", "vector_search"),
    ("장애 발생 시 복구 절차 알려줘", "vector_search"),
    ("제안서에 나온 기대 효과가 뭐야?", "vector_search"),
    ("아키텍처 설계 문서 내용 요약해줘", "vector_search"),
    ("Client-C가 쓰는 제품 알려줘", "knowledge_graph"),
    ("보안솔루션팀에 누가 있어?", "knowledge_graph"),
    ("Product-D2를 도입한 고객사는?", "knowledge_graph"),
    ("영업팀 부서장이 누구야?", "knowledge_graph"),
    ("김준혁이 담당하는 고객사는?", "knowledge_graph"),
    ("완료된 프로젝트를 이끈 직원은?", "knowledge_graph"),
]

# 어휘를 일부러 다르게 쓴 구어체 질문들 (튜닝에 사용하지 않음)
FRESH = [
    ("작년에 계약한 고객사 수를 세어줘", "nl2sql"),
    ("제품 하나당 월 이용료가 제일 저렴한 건?", "nl2sql"),
    ("티켓을 가장 많이 처리한 담당자는?", "nl2sql"),
    ("전체 직원이 몇 명이야?", "nl2sql"),
    ("매출이 가장 저조한 분기는?", "nl2sql"),
    ("Client-B와 거래하는 제품이 뭐가 있지?", "knowledge_graph"),
    ("데이터플랫폼팀 인원 알려줘", "knowledge_graph"),
    ("누가 Product-S2를 관리하고 있어?", "knowledge_graph"),
    ("박성민이 맡은 프로젝트 목록", "knowledge_graph"),
    ("Product-C2 쓰는 곳 어디야?", "knowledge_graph"),
    ("서비스 재시작이 반복되는 문제 어떻게 처리했어?", "vector_search"),
    ("고객이랑 킥오프 때 무슨 얘기 나눴어?", "vector_search"),
    ("보안 관련해서 뭘 점검했는지 알려줘", "vector_search"),
    ("시스템 요구사항이 어떻게 돼?", "vector_search"),
    ("제품 버전 올릴 때 어떻게 해?", "vector_search"),
]


def run_set(name: str, cases: list, verbose: bool = True) -> tuple:
    correct, rule_only_correct, llm_used, fails = 0, 0, 0, []
    for q, expected in cases:
        ruled = route_by_rules(q)
        if ruled is None:
            llm_used += 1
        rule_only_correct += (ruled or DEFAULT_TOOL) == expected

        got = route(q)
        ok = got == expected
        correct += ok
        if not ok:
            fails.append((q, expected, got, score_tools(q)))
        if verbose:
            tag = "LLM" if ruled is None else "규칙"
            print(f"  {'OK  ' if ok else 'FAIL'} [{tag}] [{expected:>15} -> {got:>15}] {q}")
    n = len(cases)
    print(f"  >> {name}: 최종 {correct}/{n} ({correct / n * 100:.0f}%) | "
          f"규칙만 {rule_only_correct}/{n} | LLM 폴백 발동 {llm_used}/{n}")
    return correct, n, fails


def main():
    tuned = [(q["q"], q["tool"]) for q in json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))]

    print("[TUNED] questions.json 30문항 — 이 세트로 튜닝했으므로 일반화 근거 아님")
    run_set("TUNED", tuned, verbose=False)

    print("\n[HOLDOUT] 1차 held-out 18문항 — 실패를 보고 설계를 고쳤으므로 이제 튜닝된 세트")
    run_set("HOLDOUT", HOLDOUT, verbose=False)

    print("\n[FRESH] 2차 held-out 15문항 — 튜닝에 쓰지 않음 (일반화 성능 지표)")
    _, _, fails = run_set("FRESH", FRESH)

    if fails:
        print("\n  FRESH 오분류 상세 (점수 내역):")
        for q, exp, got, sc in fails:
            print(f"    - {q!r}\n        기대={exp} 실제={got} 점수={sc}")


if __name__ == "__main__":
    main()
