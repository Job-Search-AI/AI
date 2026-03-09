"""
쿼리 전처리 및 확장 시스템
"""

import json
import re
import os
from typing import List, Dict, Set, Any
from .query_config import *

class QueryProcessor:
    """쿼리 전처리 및 확장을 담당하는 클래스"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        self.data_dir = data_dir
        self.synonyms = self._load_synonyms()
        self.locations = self._load_locations()
        self.education = self._load_education()
        
        # 확장기 초기화
        self.synonym_expander = SynonymExpander(self.synonyms)
        self.location_normalizer = LocationNormalizer(self.locations)
        self.education_normalizer = EducationNormalizer(self.education)
    
    def _load_synonyms(self) -> Dict:
        """동의어 사전 로드"""
        try:
            with open(os.path.join(self.data_dir, 'synonyms.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: synonyms.json not found. Using empty dictionary.")
            return {}
    
    def _load_locations(self) -> Dict:
        """지역명 사전 로드"""
        try:
            with open(os.path.join(self.data_dir, 'locations.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: locations.json not found. Using empty dictionary.")
            return {}
    
    def _load_education(self) -> Dict:
        """학력 사전 로드"""
        try:
            with open(os.path.join(self.data_dir, 'education.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: education.json not found. Using empty dictionary.")
            return {}
    
    def preprocess_query(self, query: str) -> str:
        """기본 쿼리 전처리"""
        if not query:
            return ""
        
        # 설정에 따른 전처리
        if PREPROCESSING_CONFIG.get("normalize_whitespace", True):
            query = re.sub(r'\s+', ' ', query.strip())
        
        if PREPROCESSING_CONFIG.get("convert_to_lowercase", True):
            query = query.lower()
        
        if PREPROCESSING_CONFIG.get("remove_special_chars", False):
            query = re.sub(r'[^\w\s가-힣]', ' ', query)
            query = re.sub(r'\s+', ' ', query.strip())
        
        return query
    
    def expand_query(self, query: str) -> Dict[str, Any]:
        """쿼리 확장 및 가중치 반환"""
        preprocessed_query = self.preprocess_query(query)
        
        expansion_result = {
            "original": preprocessed_query,
            "expanded_terms": [],
            "normalized_terms": [],
            "weights": {}
        }
        
        # 동의어 확장
        if SYNONYM_CONFIG.get("enabled", True):
            synonyms = self.synonym_expander.expand(preprocessed_query)
            expansion_result["expanded_terms"].extend(synonyms)
            for term in synonyms:
                expansion_result["weights"][term] = EXPANSION_WEIGHTS.get("synonyms", 0.8)
        
        # 지역명 정규화
        if LOCATION_CONFIG.get("enabled", True):
            normalized_locations = self.location_normalizer.normalize(preprocessed_query)
            expansion_result["normalized_terms"].extend(normalized_locations)
            for term in normalized_locations:
                expansion_result["weights"][term] = EXPANSION_WEIGHTS.get("locations", 0.9)
        
        # 학력 정규화
        if EDUCATION_CONFIG.get("enabled", True):
            normalized_education = self.education_normalizer.normalize(preprocessed_query)
            expansion_result["normalized_terms"].extend(normalized_education)
            for term in normalized_education:
                expansion_result["weights"][term] = EXPANSION_WEIGHTS.get("education", 0.8)
        
        # 원본 쿼리 가중치
        expansion_result["weights"][preprocessed_query] = EXPANSION_WEIGHTS.get("original_query", 1.0)
        
        return expansion_result
    
    def get_expanded_query_string(self, query: str) -> str:
        """확장된 쿼리를 하나의 문자열로 반환"""
        expansion_result = self.expand_query(query)
        
        all_terms = [expansion_result["original"]]
        all_terms.extend(expansion_result["expanded_terms"])
        all_terms.extend(expansion_result["normalized_terms"])
        
        # 중복 제거
        unique_terms = list(dict.fromkeys(all_terms))
        
        return " ".join(unique_terms)


class SynonymExpander:
    """동의어 확장 클래스"""
    
    def __init__(self, synonyms_dict: Dict):
        self.synonyms = synonyms_dict
        self._build_reverse_index()
    
    def _build_reverse_index(self):
        """역색인 구축 (단어 -> 카테고리 매핑)"""
        self.word_to_category = {}
        for category, subcategories in self.synonyms.items():
            for key, synonyms in subcategories.items():
                for synonym in synonyms:
                    if synonym not in self.word_to_category:
                        self.word_to_category[synonym] = []
                    self.word_to_category[synonym].append((category, key))
    
    def expand(self, query: str) -> List[str]:
        """쿼리의 동의어 확장"""
        words = query.split()
        expanded_terms = []
        
        for word in words:
            if word in self.word_to_category:
                for category, key in self.word_to_category[word]:
                    synonyms = self.synonyms[category][key]
                    # 최대 확장 개수 제한
                    max_expansions = SYNONYM_CONFIG.get("max_expansions", 3)
                    expanded_terms.extend(synonyms[:max_expansions])
        
        return list(set(expanded_terms))  # 중복 제거


class LocationNormalizer:
    """지역명 정규화 클래스"""
    
    def __init__(self, locations_dict: Dict):
        self.locations = locations_dict
        self._build_variation_map()
    
    def _build_variation_map(self):
        """지역명 변형 매핑 구축"""
        self.variation_to_standard = {}
        for location, info in self.locations.items():
            standard = info.get("standard", location)
            variations = info.get("variations", [])
            
            for variation in variations:
                self.variation_to_standard[variation] = standard
    
    def normalize(self, query: str) -> List[str]:
        """지역명 정규화"""
        words = query.split()
        normalized_terms = []
        
        for word in words:
            if word in self.variation_to_standard:
                standard = self.variation_to_standard[word]
                normalized_terms.append(standard)
                
                # 인근 지역 포함 설정이 활성화된 경우
                if LOCATION_CONFIG.get("include_nearby", False):
                    for location, info in self.locations.items():
                        if info.get("standard") == standard:
                            nearby = info.get("nearby", [])
                            normalized_terms.extend(nearby)
        
        return list(set(normalized_terms))  # 중복 제거


class EducationNormalizer:
    """학력 정규화 클래스"""
    
    def __init__(self, education_dict: Dict):
        self.education = education_dict
        self._build_variation_map()
    
    def _build_variation_map(self):
        """학력 변형 매핑 구축"""
        self.variation_to_standard = {}
        for education, info in self.education.items():
            standard = info.get("standard", education)
            variations = info.get("variations", [])
            
            for variation in variations:
                self.variation_to_standard[variation] = standard
    
    def normalize(self, query: str) -> List[str]:
        """학력 정규화"""
        words = query.split()
        normalized_terms = []
        
        for word in words:
            if word in self.variation_to_standard:
                standard = self.variation_to_standard[word]
                normalized_terms.append(standard)
                
                # 동등 학력 포함 설정이 활성화된 경우
                if EDUCATION_CONFIG.get("include_equivalent", True):
                    for education, info in self.education.items():
                        if info.get("standard") == standard:
                            equivalent = info.get("equivalent", [])
                            normalized_terms.extend(equivalent)
        
        return list(set(normalized_terms))  # 중복 제거
