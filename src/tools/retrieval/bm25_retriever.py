"""
BM25 키워드 검색 구현
"""

import math
import pickle
import os
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Any
import re

try:
    from konlpy.tag import Okt
    KONLPY_AVAILABLE = True
except ImportError:
    print("Warning: KoNLPy not available. Using simple tokenization.")
    KONLPY_AVAILABLE = False


class BM25Retriever:
    """BM25 알고리즘 기반 키워드 검색기"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: 용어 빈도 포화 매개변수 (기본값: 1.5)
            b: 문서 길이 정규화 매개변수 (기본값: 0.75)
        """
        self.k1 = k1
        self.b = b
        
        # 토크나이저 초기화
        if KONLPY_AVAILABLE:
            self.tokenizer = Okt()
        else:
            self.tokenizer = None
        
        # 인덱스 관련 변수
        self.documents = []
        self.doc_tokens = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.term_frequencies = defaultdict(lambda: defaultdict(int))
        self.document_frequencies = defaultdict(int)
        self.idf_scores = {}
        self.num_documents = 0
        
        # 인덱스 구축 여부
        self.is_indexed = False
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토크나이징"""
        if not text:
            return []
        
        # 전처리
        text = text.lower()
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        text = re.sub(r'\s+', ' ', text.strip())
        
        if self.tokenizer and KONLPY_AVAILABLE:
            try:
                # 형태소 분석 (명사, 동사, 형용사만 추출)
                tokens = self.tokenizer.pos(text)
                filtered_tokens = [
                    word for word, pos in tokens 
                    if pos in ['Noun', 'Verb', 'Adjective'] and len(word) > 1
                ]
                return filtered_tokens
            except Exception as e:
                print(f"Tokenization error: {e}. Using simple split.")
                return text.split()
        else:
            # 간단한 공백 기반 토크나이징
            return [word for word in text.split() if len(word) > 1]
    
    def build_index(self, documents: List[str]) -> None:
        """문서 컬렉션에 대한 인덱스 구축"""
        print("BM25 인덱스 구축 시작...")
        
        self.documents = documents
        self.num_documents = len(documents)
        self.doc_tokens = []
        self.doc_lengths = []
        
        # 각 문서 토크나이징 및 통계 수집
        for i, doc in enumerate(documents):
            if i % 1000 == 0:
                print(f"인덱싱 진행: {i}/{self.num_documents}")
            
            tokens = self._tokenize(doc)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            
            # 용어 빈도 계산
            token_counts = Counter(tokens)
            for term, count in token_counts.items():
                self.term_frequencies[term][i] = count
                if count > 0:
                    self.document_frequencies[term] += 1
        
        # 평균 문서 길이 계산
        self.avg_doc_length = sum(self.doc_lengths) / self.num_documents if self.num_documents > 0 else 0
        
        # IDF 점수 계산
        self._calculate_idf_scores()
        
        self.is_indexed = True
        print("BM25 인덱스 구축 완료")
    
    def _calculate_idf_scores(self) -> None:
        """IDF 점수 계산"""
        for term in self.document_frequencies:
            df = self.document_frequencies[term]
            idf = math.log((self.num_documents - df + 0.5) / (df + 0.5))
            self.idf_scores[term] = max(idf, 0)  # 음수 IDF 방지
    
    def _calculate_bm25_score(self, query_tokens: List[str], doc_id: int) -> float:
        """특정 문서에 대한 BM25 점수 계산"""
        if doc_id >= len(self.doc_tokens):
            return 0.0
        
        doc_tokens = self.doc_tokens[doc_id]
        doc_length = self.doc_lengths[doc_id]
        
        score = 0.0
        doc_token_counts = Counter(doc_tokens)
        
        for term in query_tokens:
            if term not in self.idf_scores:
                continue
            
            tf = doc_token_counts.get(term, 0)
            if tf == 0:
                continue
            
            idf = self.idf_scores[term]
            
            # BM25 공식
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def search(self, query: str, top_k: int = 10) -> Tuple[List[str], List[float]]:
        """BM25 검색 수행"""
        if not self.is_indexed:
            raise ValueError("인덱스가 구축되지 않았습니다. build_index()를 먼저 호출하세요.")
        
        if not query.strip():
            return [], []
        
        # 쿼리 토크나이징
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [], []
        
        # 모든 문서에 대해 BM25 점수 계산
        doc_scores = []
        for doc_id in range(self.num_documents):
            score = self._calculate_bm25_score(query_tokens, doc_id)
            if score > 0:
                doc_scores.append((doc_id, score))
        
        # 점수 기준 정렬
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 k개 결과 반환
        top_results = doc_scores[:top_k]
        
        retrieved_docs = [self.documents[doc_id] for doc_id, _ in top_results]
        scores = [score for _, score in top_results]
        
        return retrieved_docs, scores
    
    def get_term_statistics(self, term: str) -> Dict[str, Any]:
        """특정 용어의 통계 정보 반환"""
        if not self.is_indexed:
            return {}
        
        return {
            "document_frequency": self.document_frequencies.get(term, 0),
            "idf_score": self.idf_scores.get(term, 0),
            "collection_frequency": sum(self.term_frequencies[term].values())
        }
    
    def save_index(self, filepath: str) -> None:
        """인덱스를 파일로 저장"""
        if not self.is_indexed:
            raise ValueError("저장할 인덱스가 없습니다.")
        
        index_data = {
            "k1": self.k1,
            "b": self.b,
            "documents": self.documents,
            "doc_tokens": self.doc_tokens,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "term_frequencies": dict(self.term_frequencies),
            "document_frequencies": dict(self.document_frequencies),
            "idf_scores": self.idf_scores,
            "num_documents": self.num_documents
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"인덱스가 {filepath}에 저장되었습니다.")
    
    def load_index(self, filepath: str) -> None:
        """파일에서 인덱스 로드"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"인덱스 파일을 찾을 수 없습니다: {filepath}")
        
        with open(filepath, 'rb') as f:
            index_data = pickle.load(f)
        
        self.k1 = index_data["k1"]
        self.b = index_data["b"]
        self.documents = index_data["documents"]
        self.doc_tokens = index_data["doc_tokens"]
        self.doc_lengths = index_data["doc_lengths"]
        self.avg_doc_length = index_data["avg_doc_length"]
        self.term_frequencies = defaultdict(lambda: defaultdict(int), index_data["term_frequencies"])
        self.document_frequencies = defaultdict(int, index_data["document_frequencies"])
        self.idf_scores = index_data["idf_scores"]
        self.num_documents = index_data["num_documents"]
        
        self.is_indexed = True
        print(f"인덱스가 {filepath}에서 로드되었습니다.")
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """인덱스 통계 정보 반환"""
        if not self.is_indexed:
            return {}
        
        return {
            "num_documents": self.num_documents,
            "num_unique_terms": len(self.idf_scores),
            "avg_doc_length": self.avg_doc_length,
            "total_tokens": sum(self.doc_lengths),
            "parameters": {"k1": self.k1, "b": self.b}
        }
