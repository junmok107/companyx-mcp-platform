"""Ollama 로컬 LLM 호출 공통 클라이언트 (nl2sql/llm_client.py와 동일 — 도구별로 독립 모듈 유지)."""

import json
import os
import urllib.request

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:9b")


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
