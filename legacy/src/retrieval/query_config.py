"""
쿼리 처리 관련 설정
"""

# 동의어 확장 설정
SYNONYM_CONFIG = {
    "enabled": True,
    "max_expansions": 3,  # 각 용어당 최대 확장 개수
    "similarity_threshold": 0.8  # 동의어 유사도 임계값
}

# 지역명 정규화 설정
LOCATION_CONFIG = {
    "enabled": True,
    "normalize_variations": True,  # 지역명 변형 정규화
    "include_nearby": False  # 인근 지역 포함 여부
}

# 학력 표준화 설정
EDUCATION_CONFIG = {
    "enabled": True,
    "normalize_levels": True,  # 학력 수준 정규화
    "include_equivalent": True  # 동등 학력 포함
}

# 직무 카테고리 설정
JOB_CATEGORY_CONFIG = {
    "enabled": True,
    "expand_categories": True,  # 직무 카테고리 확장
    "include_related": True  # 관련 직무 포함
}

# 쿼리 전처리 설정
PREPROCESSING_CONFIG = {
    "remove_stopwords": True,
    "normalize_whitespace": True,
    "convert_to_lowercase": True,
    "remove_special_chars": False
}

# 확장 가중치 설정
EXPANSION_WEIGHTS = {
    "original_query": 1.0,
    "synonyms": 0.8,
    "categories": 0.7,
    "locations": 0.9,
    "education": 0.8
}
