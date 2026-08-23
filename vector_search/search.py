"""Step 1: 질의 임베딩 + pgvector 코사인 유사도 Top-K 검색."""

import os

import psycopg
from llm_client import embed_query

DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=postgres")


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


if __name__ == "__main__":
    for r in search_chunks("SSL 인증서 관련 장애가 있었어?", top_k=5):
        print(f"[{r['similarity']:.3f}] {r['doc_id']} ({r['metadata']['type']}) - {r['content'][:40]!r}")
