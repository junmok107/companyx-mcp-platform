"""Step 1: 하이브리드 후보 검색 — pgvector 코사인 유사도 + 어휘 일치.

벡터 검색만으로는 정답 청크가 후보에 아예 들어오지 못하는 경우가 있다.
(감사 실측: "인증 토큰 규격이 궁금해"에서 'Bearer 토큰'을 담은 DOC-015/020이
 186청크 중 상위 100 후보에도 들지 못했다. 재순위 로직으로는 복구가 불가능하다.)
질의어를 직접 포함하는 청크를 어휘 검색으로 함께 끌어와 후보에 합친다.
두 경로 모두 같은 코사인 유사도를 함께 계산해 이후 단계가 동일하게 다룰 수 있게 한다.
"""

import os

import psycopg
from korean import terms as _terms
from llm_client import embed_query

# 조회 전용 role로 접속 (sql/03-roles.sql 참고). 적재는 embed.py가 별도 관리자 계정으로 수행한다.
DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=mcp_reader")

LEXICAL_TERM_LIMIT = 6    # ILIKE 조건 수 상한
LEXICAL_ROW_LIMIT = 40


def _row_to_dict(row) -> dict:
    doc_id, chunk_index, content, metadata, similarity = row
    return {
        "doc_id": doc_id,
        "chunk_index": chunk_index,
        "content": content,
        "metadata": metadata,
        "similarity": float(similarity),
    }


def _lexical_terms(query: str) -> list[str]:
    """질의에서 검색에 쓸 어휘를 길이 순으로 고른다 (긴 단어가 더 변별력 있다)."""
    return sorted(_terms(query), key=len, reverse=True)[:LEXICAL_TERM_LIMIT]


def search_chunks(query: str, top_k: int = 5) -> list[dict]:
    query_vec = embed_query(query)
    lex_terms = _lexical_terms(query)

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

            if lex_terms:
                clause = " OR ".join(["content ILIKE %s"] * len(lex_terms))
                cur.execute(
                    f"""
                    SELECT doc_id, chunk_index, content, metadata,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM document_chunks
                    WHERE {clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_vec, *[f"%{t}%" for t in lex_terms], query_vec, LEXICAL_ROW_LIMIT),
                )
                rows += cur.fetchall()

    seen, results = set(), []
    for row in rows:
        key = (row[0], row[1])
        if key in seen:
            continue
        seen.add(key)
        results.append(_row_to_dict(row))
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
