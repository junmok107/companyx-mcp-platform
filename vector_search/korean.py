"""한국어 어휘 정규화 — 관련성 게이트와 리랭킹이 공유한다.

한국어는 조사가 명사에 붙어 하나의 어절이 되므로, 어절을 그대로 토큰으로 쓰면
질문의 "백업은"과 문서의 "백업"이 서로 다른 토큰이 되어 겹침이 0이 된다.
(감사 실측: "백업은 어디에 저장돼?"가 백업 내용을 담은 문서와 교집합 0으로 판정되어
 "관련 문서를 찾지 못했습니다"를 반환했다. 8개 질문 중 3개가 이 원인으로 검색 실패.)
따라서 비교 전에 조사를 떼어낸 어간을 함께 생성한다.
"""

import re

# 긴 것부터 검사해야 "으로는"이 "는"으로 잘못 잘리지 않는다.
PARTICLES = sorted(
    [
        "으로써", "으로서", "이라고", "라고", "에서는", "에게는", "으로는", "에서도",
        "까지", "부터", "에서", "에게", "한테", "으로", "이나", "이란", "라는", "이는",
        "은", "는", "이", "가", "을", "를", "에", "의", "도", "만", "와", "과", "로", "나", "랑", "께",
    ],
    key=len,
    reverse=True,
)

# 질문 문형에 흔히 쓰여 변별력이 없는 어휘
STOPWORDS = {
    "알려줘", "뭐야", "있어", "어떻게", "되어", "보여줘", "내용", "관련", "방법",
    "궁금해", "무엇", "얼마", "언제", "해줘", "대해", "누구", "이야", "인가",
    "어디", "무슨", "그거", "정리", "이랑", "그리고", "우리", "지금", "현재",
}

# 문서는 영문 표기, 질문은 한글 음차를 쓰는 경우가 흔해 어휘 겹침이 0이 된다.
SYNONYMS = {
    "쿠버네티스": "kubernetes", "파드": "pod", "도커": "docker",
    "레디스": "redis", "에스에스엘": "ssl", "에이피아이": "api",
    "커넥션": "connection", "풀": "pool", "로그": "log",
}

_WORD = re.compile(r"[가-힣A-Za-z0-9]+")


def _strip_particle(token: str) -> str:
    for p in PARTICLES:
        # 조사를 떼고도 2글자 이상 남을 때만 어간으로 인정한다.
        if token.endswith(p) and len(token) - len(p) >= 2:
            return token[: -len(p)]
    return token


def terms(text: str) -> set:
    """비교용 어휘 집합. 원형과 조사를 뗀 어간을 모두 포함한다."""
    out = set()
    for raw in _WORD.findall(text):
        w = raw.lower()
        if len(w) < 2:
            continue
        for form in (w, _strip_particle(w)):
            if len(form) >= 2 and form not in STOPWORDS:
                out.add(SYNONYMS.get(form, form))
    return out
