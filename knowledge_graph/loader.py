"""graph/nodes.json, graph/edges.json을 networkx 그래프로 로드한다."""

import json
from pathlib import Path

import networkx as nx

GRAPH_DIR = Path(__file__).resolve().parent.parent / "graph"


def load_graph() -> nx.MultiDiGraph:
    nodes = json.loads((GRAPH_DIR / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((GRAPH_DIR / "edges.json").read_text(encoding="utf-8"))

    g = nx.MultiDiGraph()
    for n in nodes:
        g.add_node(n["id"], type=n["type"], name=n["name"], **n.get("properties", {}))
    for e in edges:
        g.add_edge(e["source"], e["target"], relation=e["relation"], **(e.get("properties") or {}))
    return g


def build_name_index(g: nx.MultiDiGraph) -> dict:
    """표시 이름(예: "Client-A", "Product-C1", 직원 실명) -> 노드 id 매핑.

    질문에서 추출된 엔티티 문자열로 실제 노드를 찾을 때 사용한다.
    """
    index = {}
    for node_id, data in g.nodes(data=True):
        index[data["name"]] = node_id
    return index


if __name__ == "__main__":
    g = load_graph()
    print(f"노드 {g.number_of_nodes()}개, 엣지 {g.number_of_edges()}개")

    by_type = {}
    for _, data in g.nodes(data=True):
        by_type[data["type"]] = by_type.get(data["type"], 0) + 1
    print("노드 타입별 개수:", by_type)

    by_relation = {}
    for _, _, data in g.edges(data=True):
        by_relation[data["relation"]] = by_relation.get(data["relation"], 0) + 1
    print("관계 타입별 개수:", by_relation)

    idx = build_name_index(g)
    print("이름 인덱스 샘플:", list(idx.items())[:3])
