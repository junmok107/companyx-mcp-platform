"""학생 분류기용 특징 추출 — 질문을 '의도 신호'의 수치 벡터로 바꾼다.

임베딩(nomic)이 라우팅 의도를 담지 못함이 실측돼(CV 0.60), 임베딩 대신 의도를
직접 가리키는 명시적 특징을 쓴다. 키워드 라우터가 '손으로 정한 가중치'로 점수를 냈다면,
여기서는 같은 종류의 신호를 '특징'으로 노출하고 가중치는 학습(로지스틱 회귀)이 정한다.

특징은 char n-gram(어휘 변형에 강함) + 의도 표지 카운트를 결합한다.
"""

import re

# 의도 표지 그룹 — 각 그룹의 등장 횟수를 특징으로 낸다 (가중치는 학습이 정함)
AGG_MARKERS = ["매출", "연봉", "급여", "금액", "가격", "단가", "예산", "건수", "개수",
               "합계", "평균", "총", "몇", "세어", "집계", "순위", "상위", "비싼", "저렴", "분포"]
REL_MARKERS = ["담당", "소속", "속한", "맡", "이끄", "이끌", "리드", "책임", "총괄", "수장",
               "팀장", "부서장", "사용", "쓰는", "쓴", "채택", "들여", "운용", "도입",
               "관련", "엮", "연관", "이슈", "불만", "누구", "명단", "인원"]
DOC_MARKERS = ["장애", "사고", "먹통", "멎", "멈춘", "원인", "복구", "절차", "대응", "조치",
               "설치", "구축", "가이드", "매뉴얼", "튜닝", "최적화", "방법", "아키텍처",
               "회의", "미팅", "논의", "마일스톤", "제안서", "정책", "방침", "취약점", "점검",
               "백업", "보관", "로그", "모니터링", "인증", "엔드포인트", "배포", "업그레이드", "문서"]
TABLE_MARKERS = ["티켓", "계약", "분기", "카테고리", "우선순위", "활성", "등록", "미해결", "규모"]

ENTITY_NAME = re.compile(r"(client|product)-[a-z0-9]+", re.IGNORECASE)
ENTITY_TYPE = ["고객사", "고객", "거래처", "업체", "제품", "솔루션", "상품",
               "직원", "인력", "프로젝트", "부서", "엔지니어", "담당자"]
REGION = re.compile(r"서울|경기|인천|대전|대구|부산|광주|제주")
PERIOD = re.compile(r"\d{4}\s*년|\d\s*분기|작년|재작년|올해|상반기|하반기")

FEATURE_NAMES = [
    "agg", "rel", "doc", "table", "entity_name", "entity_type",
    "region", "period", "has_superlative", "len_bucket",
]


def count(text, markers):
    return sum(text.count(m) for m in markers)


def intent_features(question: str) -> dict:
    q = question.lower()
    feats = {
        "agg": count(q, AGG_MARKERS),
        "rel": count(q, REL_MARKERS),
        "doc": count(q, DOC_MARKERS),
        "table": count(q, TABLE_MARKERS),
        "entity_name": 1 if ENTITY_NAME.search(question) else 0,
        "entity_type": count(q, ENTITY_TYPE),
        "region": 1 if REGION.search(question) else 0,
        "period": 1 if PERIOD.search(question) else 0,
        "has_superlative": 1 if re.search(r"가장|제일|최다|최소|최고", q) else 0,
        "len_bucket": min(len(question) // 15, 4),
    }
    return feats


def intent_vector(question: str) -> list[int]:
    f = intent_features(question)
    return [f[k] for k in FEATURE_NAMES]
