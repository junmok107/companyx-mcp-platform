"""라우터 분류용 임베딩 유틸. Ollama nomic-embed-text를 재사용한다.

주의: 앞선 IR 평가에서 이 모델이 짧은 한국어 문장 변별에 약함이 실측됐다.
라우팅도 짧은 질문이므로, 본격 학습 전에 분리 가능성을 먼저 확인해야 한다.
분류 질의에는 nomic의 'classification:' 프리픽스를 쓴다(검색용 search_query와 구분).
"""

import json
import os
import time
import urllib.request

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def embed_one(text: str, prefix: str = "classification: ", timeout: int = 30) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": f"{prefix}{text}"}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))["embedding"]


def embed_many(texts: list[str], prefix: str = "classification: ", verbose: bool = False) -> list[list[float]]:
    out = []
    t0 = time.time()
    for i, t in enumerate(texts):
        out.append(embed_one(t, prefix))
        if verbose and (i + 1) % 20 == 0:
            print(f"  임베딩 {i+1}/{len(texts)}  ({(time.time()-t0)/(i+1)*1000:.0f}ms/건)")
    return out
