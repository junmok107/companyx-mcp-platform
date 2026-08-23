"""Ollama 임베딩(nomic-embed-text) + 생성(gemma2:9b) 클라이언트."""

import json
import os
import urllib.request

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:9b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def embed_document(text: str, timeout: int = 30) -> str:
    """문서 청크 임베딩용. nomic-embed-text는 'search_document:' 프리픽스가 없으면 검색 품질이 크게 떨어진다."""
    return embed_text(f"search_document: {text}", timeout=timeout)


def embed_query(text: str, timeout: int = 30) -> str:
    """질의 임베딩용. 문서와 다른 프리픽스('search_query:')를 붙여야 nomic-embed-text가 제대로 동작한다."""
    return embed_text(f"search_query: {text}", timeout=timeout)


def embed_text(text: str, timeout: int = 30) -> str:
    """텍스트를 임베딩하고 pgvector에 바로 넣을 수 있는 문자열 '[v1,v2,...]'로 반환한다."""
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    vec = body["embedding"]
    return "[" + ",".join(str(x) for x in vec) + "]"


def call_ollama(prompt: str, model: str | None = None, timeout: int = 120, temperature: float = 0.0) -> str:
    payload = json.dumps({
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["response"].strip()
