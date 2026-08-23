"""Step 1: 질의 임베딩 + pgvector 코사인 유사도 Top-K 검색."""

import os

import psycopg
from llm_client import embed_query

# 조회 전용 role로 접속 (sql/03-roles.sql 참고). 적재는 embed.py가 별도 관리자 계정으로 수행한다.
DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=mcp_reader")


def search_chunks(query: str, top_k: int = 5) -> list[dict]:
    query_vec = embed_query(query)

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doc_id, chunk_index, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vec, query_vec, top_k),
            )
            rows = cur.fetchall()

    results = []
    for doc_id, chunk_index, content, metadata, similarity in rows:
        results.append({
            "doc_id": doc_id,
            "chunk_index": chunk_index,
            "content": content,
            "metadata": metadata,
            "similarity": float(similarity),
        })
    return results


def fetch_document_chunks(doc_id: str) -> list[dict]:
    """한 문서의 모든 청크를 원래 순서대로 가져온다.

    청크 단위로 검색하되 컨텍스트는 문서 단위로 제공하기 위한 조회(parent document retrieval).
    이 데이터셋의 문서는 20~30줄로 짧아 전체를 넣어도 프롬프트 부담이 작고,
    질문이 가리키는 섹션(예: "대응 방법" -> 조치 사항)이 유사도 상위에 들지 못해
    누락되는 문제를 구조적으로 없앨 수 있다.
    """
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT doc_id, chunk_index, content, metadata FROM document_chunks "
                "WHERE doc_id = %s ORDER BY chunk_index",
                (doc_id,),
            )
            rows = cur.fetchall()

    return [
        {"doc_id": d, "chunk_index": i, "content": c, "metadata": m, "similarity": 1.0}
        for d, i, c, m in rows
    ]


if __name__ == "__main__":
    for r in search_chunks("SSL 인증서 관련 장애가 있었어?", top_k=5):
        print(f"[{r['similarity']:.3f}] {r['doc_id']} ({r['metadata']['type']}) - {r['content'][:40]!r}")
