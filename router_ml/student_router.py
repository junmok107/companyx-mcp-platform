"""학생 분류기 추론 래퍼 — 학습된 모델을 로드해 질문을 도구로 분류한다.

교사 LLM 없이 밀리초 단위로 동작한다. 확신도(최대 확률)가 낮으면 None을 반환해,
호출부가 LLM 폴백으로 넘길 수 있게 한다 (증류 모델도 확신 없는 질문은 있으므로).
"""

import sys
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from features import intent_vector  # noqa: E402

MODEL_PATH = HERE / "student_model.joblib"
_MODEL = None


def _load():
    global _MODEL
    if _MODEL is None:
        _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def _featurize(m, question):
    char = m["vec"].transform([question])
    intent = csr_matrix(np.array([intent_vector(question)], dtype=float))
    return hstack([char, intent]).tocsr()


def classify(question: str, min_confidence: float = 0.0):
    """(tool, confidence) 반환. confidence < min_confidence면 (None, confidence)."""
    m = _load()
    X = _featurize(m, question)
    proba = m["clf"].predict_proba(X)[0]
    idx = int(np.argmax(proba))
    conf = float(proba[idx])
    tool = m["clf"].classes_[idx]
    if conf < min_confidence:
        return None, conf
    return tool, conf


if __name__ == "__main__":
    for q in ["활성 계약이 몇 건이야", "Client-A가 쓰는 제품은", "서버 장애 원인이 뭐였어",
              "영업팀 직원 수가 몇 명이야", "그거 어떻게 됐어"]:
        t, c = classify(q)
        print(f"  {t:<16} conf={c:.2f}  | {q}")
