"""documents/*.md 40건을 청킹하고 Ollama(nomic-embed-text)로 임베딩해 document_chunks에 적재.

주의: 이 파일은 원래 팀원 담당(임베딩 파이프라인)이지만, 벡터 검색 랭킹 로직(내 담당)을
막고 있어서 최소 구현으로 대신 만들어둔 것. 팀원이 검토/교체해도 된다.

청킹 전략: 마크다운 "## " 섹션 단위로 쪼갠다. 문서가 20~30줄 내외로 짧아서
섹션 하나가 곧 하나의 의미 단위(기본 정보/원인 분석/조치 사항 등)가 된다.
"""

import json
import os
import re
from pathlib import Path

import psycopg
from llm_client import embed_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
DB_DSN = os.environ.get("COMPANYX_DB_DSN", "dbname=companyx host=localhost port=5434 user=postgres")


def chunk_document(text: str) -> list[str]:
    """"# 제목" 아래를 "## "와 "### " 섹션 단위로 쪼갠다 (더 얕은 헤더만 있으면 그걸로 쪼갬).

    "## " 단위로만 쪼개면 그 아래 여러 "### " 하위 섹션(예: 모니터링/백업/로그 관리)이
    한 청크에 뭉쳐서 임베딩이 희석되는 문제가 실측되어, 존재하는 가장 세분화된 헤더 레벨로 쪼갠다.
    각 청크 앞에 문서 제목을 붙여 맥락을 유지한다.
    """
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    body = lines[1:]

    split_prefix = "### " if any(l.startswith("### ") for l in body) else "## "

    sections = []
    current = []
    for line in body:
        if line.startswith(split_prefix):
            if current:
                sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())

    chunks = [f"{title}\n{s}".strip() for s in sections if s.strip()]
    return chunks or [text.strip()]


def load_documents() -> list[dict]:
    index = json.loads((DOCUMENTS_DIR / "index.json").read_text(encoding="utf-8"))
    docs = []
    for entry in index:
        content = (DOCUMENTS_DIR / entry["filename"]).read_text(encoding="utf-8")
        docs.append({**entry, "content": content})
    return docs


def run_pipeline():
    docs = load_documents()
    total_chunks = 0

    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM document_chunks")  # 재실행 시 중복 적재 방지
            for doc in docs:
                chunks = chunk_document(doc["content"])
                for i, chunk_text in enumerate(chunks):
                    vec = embed_document(chunk_text)
                    metadata = {"type": doc["type"], "title": doc["title"]}
                    cur.execute(
                        "INSERT INTO document_chunks (doc_id, chunk_index, content, embedding, metadata) "
                        "VALUES (%s, %s, %s, %s::vector, %s)",
                        (doc["id"], i, chunk_text, vec, json.dumps(metadata, ensure_ascii=False)),
                    )
                    total_chunks += 1
                print(f"{doc['id']} ({doc['type']}): {len(chunks)}개 청크 적재")

    print(f"\n총 {len(docs)}개 문서, {total_chunks}개 청크 적재 완료")


if __name__ == "__main__":
    run_pipeline()
