"""LLM 증류 3단계 — 학생 분류기 학습.

특징: char n-gram TF-IDF (어휘 변형·오타에 강함) + 의도 표지 카운트(features.py).
두 특징을 결합해 로지스틱 회귀를 학습한다. 학습된 모델은 joblib로 저장하고,
router가 추론 시 로드해 밀리초 단위로 분류한다 (교사 LLM 없이).
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import cross_val_predict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import FEATURE_NAMES, intent_vector  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "trainset_clean.jsonl"
MODEL_PATH = HERE / "student_model.joblib"
TOOLS = ["nl2sql", "knowledge_graph", "vector_search"]


def load():
    rows = [json.loads(l) for l in DATA_PATH.open(encoding="utf-8")]
    return [r["question"] for r in rows], [r["label"] for r in rows]


def build_features(texts, vec=None, fit=False):
    if fit:
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)
        char = vec.fit_transform(texts)
    else:
        char = vec.transform(texts)
    intent = csr_matrix(np.array([intent_vector(t) for t in texts], dtype=float))
    X = hstack([char, intent]).tocsr()
    return X, vec


def main():
    texts, y = load()
    y = np.array(y)
    print(f"학습셋 {len(texts)}개")

    X, vec = build_features(texts, fit=True)
    clf = LogisticRegression(max_iter=3000, C=4, class_weight="balanced")

    # 교차검증으로 일반화 성능 추정 (같은 데이터 재사용 방지)
    pred = cross_val_predict(clf, X, y, cv=5)
    acc = accuracy_score(y, pred)
    f1 = f1_score(y, pred, average="macro", labels=TOOLS)
    print(f"\n5-fold CV accuracy: {acc:.3f}  macro F1: {f1:.3f}")
    cm = confusion_matrix(y, pred, labels=TOOLS)
    print("Confusion (행=정답,열=예측):")
    print(f"  {'':<16}" + "".join(f"{t[:8]:>10}" for t in TOOLS))
    for i, t in enumerate(TOOLS):
        print(f"  {t:<16}" + "".join(f"{cm[i][j]:>10}" for j in range(3)))

    # 전체로 재학습해 저장
    clf.fit(X, y)
    joblib.dump({"clf": clf, "vec": vec, "tools": TOOLS, "feature_names": FEATURE_NAMES}, MODEL_PATH)
    print(f"\n모델 저장: {MODEL_PATH}")


if __name__ == "__main__":
    main()
