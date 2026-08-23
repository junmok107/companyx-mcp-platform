"""extract.py가 만든 스펙(JSON)을 받아 실제로 그래프를 순회한다."""


def _step(g, node_ids, relation, direction):
    result = set()
    for node_id in node_ids:
        if node_id not in g:
            continue
        if direction == "outgoing":
            for _, target, data in g.out_edges(node_id, data=True):
                if data["relation"] == relation:
                    result.add(target)
        else:
            for source, _, data in g.in_edges(node_id, data=True):
                if data["relation"] == relation:
                    result.add(source)
    return result


def describe_nodes(g, node_ids) -> list[dict]:
    """탐색 결과를 노드 id 순으로 정렬해 반환한다.

    _step()이 집합을 반환하므로 정렬하지 않으면 파이썬 해시 랜덤화 때문에 같은 질문이
    프로세스마다 다른 순서로 답변된다(실측: 동일 질의 3회 실행에서 10명의 순서가 매번 상이).
    내용은 같지만 재현이 불가능해지고 사용자에게는 불안정해 보이므로 순서를 고정한다.
    """
    described = []
    for node_id in sorted(node_ids):
        data = dict(g.nodes[node_id])
        data["id"] = node_id
        described.append(data)
    return described


def run_traverse(g, spec: dict, name_index: dict) -> dict:
    entity_name = spec["entity"]
    if entity_name not in name_index:
        return {"error": f"'{entity_name}'를 그래프에서 찾을 수 없습니다.", "nodes": []}

    node_ids = {name_index[entity_name]}
    for hop in spec["hops"]:
        node_ids = _step(g, node_ids, hop["relation"], hop["direction"])
        if not node_ids:
            break

    return {"nodes": describe_nodes(g, node_ids)}


def run_filtered_traverse(g, spec: dict) -> dict:
    node_type = spec["node_type"]
    filt = spec.get("filter", {})
    node_ids = {
        n for n, d in g.nodes(data=True)
        if d.get("type") == node_type and all(d.get(k) == v for k, v in filt.items())
    }

    for hop in spec["hops"]:
        node_ids = _step(g, node_ids, hop["relation"], hop["direction"])
        if not node_ids:
            break

    return {"nodes": describe_nodes(g, node_ids)}


def run_aggregate(g, spec: dict) -> dict:
    relation = spec["relation"]
    group_by = spec["group_by"]
    order = spec.get("order", "desc")
    limit = spec.get("limit", 1)

    counts: dict[str, int] = {}
    for source, target, data in g.edges(data=True):
        if data["relation"] != relation:
            continue
        key = source if group_by == "source" else target
        counts[key] = counts.get(key, 0) + 1

    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=(order == "desc"))
    # 동점 포함: limit번째와 같은 개수인 항목은 모두 반환한다.
    # 단순히 [:limit]로 자르면 "가장 많은 X는?"에서 공동 1위 중 하나만 임의로 남아
    # 나머지가 조용히 사라진다 (실측: MANAGES_ACCOUNT 공동 1위 3명 중 1명만 답변됨).
    ranked = ordered[:limit]
    if ordered and len(ordered) > limit:
        cutoff = ordered[limit - 1][1]
        ranked += [kv for kv in ordered[limit:] if kv[1] == cutoff]

    nodes = []
    for node_id, count in ranked:
        data = dict(g.nodes[node_id])
        data["id"] = node_id
        data["count"] = count
        nodes.append(data)

    return {"nodes": nodes}


def execute(g, spec: dict, name_index: dict) -> dict:
    mode = spec.get("mode")
    if mode == "traverse":
        return run_traverse(g, spec, name_index)
    if mode == "filtered_traverse":
        return run_filtered_traverse(g, spec)
    if mode == "aggregate":
        return run_aggregate(g, spec)
    return {"error": f"알 수 없는 모드입니다: {mode}", "nodes": []}


if __name__ == "__main__":
    from loader import build_name_index, load_graph

    g = load_graph()
    idx = build_name_index(g)

    spec1 = {"mode": "traverse", "entity": "Client-A", "hops": [{"relation": "USES", "direction": "outgoing"}]}
    print(execute(g, spec1, idx))

    spec2 = {"mode": "aggregate", "relation": "REPORTED_ISSUE", "group_by": "target", "order": "desc", "limit": 1}
    print(execute(g, spec2, idx))
