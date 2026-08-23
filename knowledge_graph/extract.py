"""자연어 질문 -> 그래프 탐색 스펙(JSON) 추출.

3가지 모드를 지원한다:
- traverse: 특정 엔티티에서 시작해 1~2홉 탐색
- filtered_traverse: 속성으로 노드를 필터링한 뒤 관계 탐색 (예: 진행중인 프로젝트를 이끄는 직원)
- aggregate: 관계를 카운트해서 집계 (예: 이슈가 가장 많은 제품)
"""

import json
import re
from pathlib import Path

from llm_client import call_ollama

GRAPH_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "graph" / "schema.md"

RULES = """\
당신은 지식 그래프 탐색 질문을 구조화된 JSON 스펙으로 변환하는 어시스턴트다.
아래 그래프 스키마를 참고해서, 질문을 다음 세 가지 모드 중 하나의 JSON으로 변환한다.

1. traverse: 질문에 특정 엔티티 이름(예: "Client-A", "Product-C1", 부서명, 사람 이름)이 명시된 경우.
   {"mode": "traverse", "entity": "<질문에 언급된 이름 그대로>", "hops": [{"relation": "<관계명>", "direction": "outgoing|incoming"}, ...]}
   - direction은 관계의 정의 방향(source->target) 기준. 엔티티가 source면 outgoing, target이면 incoming.
   - 2단계 탐색이 필요하면 hops에 두 개를 순서대로 넣는다.

2. filtered_traverse: 특정 이름이 아니라 "진행중인 프로젝트", "완료된 프로젝트"처럼 속성으로 노드 집합을 먼저 골라야 하는 경우.
   {"mode": "filtered_traverse", "node_type": "<노드 타입>", "filter": {"<속성명>": "<값>"}, "hops": [{"relation": "...", "direction": "..."}]}

3. aggregate: "가장 많은/적은 ~인 X는?"처럼 관계 개수를 세서 순위를 매기는 경우 (특정 엔티티 없음).
   {"mode": "aggregate", "relation": "<관계명>", "group_by": "source|target", "order": "desc|asc", "limit": <숫자>}
   - group_by는 카운트를 어느 쪽 노드 기준으로 묶을지: 관계의 source 쪽 노드별로 세면 "source", target 쪽 노드별로 세면 "target".

출력은 JSON 객체 하나만 반환한다. 설명이나 마크다운 코드펜스를 포함하지 않는다.

주의: "X부/X팀 소속 직원", "X부서 소속" 같은 질문은 employee 노드에 부서명을 속성으로 갖고 있지 않다.
반드시 mode="traverse"로 부서 이름을 entity로 두고 BELONGS_TO를 incoming으로 탐색해야 한다
(filtered_traverse로 employee를 부서명 속성으로 필터링하려 하면 0건이 나온다 — 절대 이렇게 하지 말 것).
"""

FEW_SHOT_EXAMPLES = [
    # 주의: 실제 테스트셋(questions.json)과 문장이 겹치지 않게 유지 (NL2SQL에서 겹쳐서 오답났던 전례 있음)
    {
        "question": "Client-B가 사용 중인 제품은 무엇인가?",
        "spec": {"mode": "traverse", "entity": "Client-B", "hops": [{"relation": "USES", "direction": "outgoing"}]},
    },
    {
        "question": "Product-S2를 사용하는 고객사 목록은?",
        "spec": {"mode": "traverse", "entity": "Product-S2", "hops": [{"relation": "USES", "direction": "incoming"}]},
    },
    {
        "question": "데이터플랫폼팀에 속한 직원은 누구야?",
        "spec": {"mode": "traverse", "entity": "데이터플랫폼팀", "hops": [{"relation": "BELONGS_TO", "direction": "incoming"}]},
    },
    {
        "question": "Product-S3와 관련 있는 프로젝트는?",
        "spec": {
            "mode": "traverse",
            "entity": "Product-S3",
            "hops": [
                {"relation": "USES", "direction": "incoming"},
                {"relation": "HAS_PROJECT", "direction": "outgoing"},
            ],
        },
    },
    {
        "question": "완료된 프로젝트를 이끄는 직원은 누구야?",
        "spec": {
            "mode": "filtered_traverse",
            "node_type": "project",
            "filter": {"status": "completed"},
            "hops": [{"relation": "LEADS", "direction": "incoming"}],
        },
    },
    {
        "question": "가장 많은 프로젝트를 담당하는 매니저는?",
        "spec": {"mode": "aggregate", "relation": "LEADS", "group_by": "source", "order": "desc", "limit": 1},
    },
    {
        "question": "보안 이슈가 가장 적게 접수된 제품은?",
        "spec": {"mode": "aggregate", "relation": "REPORTED_ISSUE", "group_by": "target", "order": "asc", "limit": 1},
    },
    {
        "question": "보안솔루션팀 팀장은 누구야?",
        "spec": {"mode": "traverse", "entity": "보안솔루션팀", "hops": [{"relation": "HEAD_IS", "direction": "outgoing"}]},
    },
]


PROPERTY_VALUE_NOTES = """\
[노드 속성 실제 값] (filter에 쓸 값은 반드시 아래 값 중에서만 고른다 — 지어내지 말 것)
- client.industry: 금융, 제조업, 미디어, 교육, 의료/바이오, 유통/물류, IT/SW, 공공기관, 에너지, 건설
- client.region: 서울, 경기, 인천, 대전, 대구, 부산, 광주, 제주
- client.size: startup, mid, enterprise
- product.category: cloud, security, data, consulting
- project.status: planning, in_progress, on_hold, completed  (주의: "진행중"은 in_progress이지 ongoing이 아니다)
"""


def _load_schema() -> str:
    return GRAPH_SCHEMA_PATH.read_text(encoding="utf-8") + "\n" + PROPERTY_VALUE_NOTES


def _format_few_shot() -> str:
    blocks = []
    for ex in FEW_SHOT_EXAMPLES:
        blocks.append(f"질문: {ex['question']}\nJSON: {json.dumps(ex['spec'], ensure_ascii=False)}")
    return "\n\n".join(blocks)


def build_extract_prompt(question: str) -> str:
    return (
        f"{RULES}\n\n[그래프 스키마]\n{_load_schema()}\n\n"
        f"[예시]\n{_format_few_shot()}\n\n질문: {question}\nJSON:"
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"JSON을 찾을 수 없습니다: {text!r}")
    return json.loads(match.group(0))


def extract_spec(question: str) -> dict:
    raw = call_ollama(build_extract_prompt(question))
    return _extract_json(raw)


if __name__ == "__main__":
    for q in ["Client-A가 사용 중인 제품 목록은?", "기술 지원 이슈가 가장 많은 제품은?"]:
        print(q, "->", extract_spec(q))
