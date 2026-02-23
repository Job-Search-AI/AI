"""
하이브리드 검색 시스템 (BM25 + 임베딩 검색)
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from sklearn.preprocessing import MinMaxScaler
import sys
import os

# 프로젝트 경로 추가
sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from .bm25_retriever import BM25Retriever
from .query_processor import QueryProcessor
from src.embedding.model import similarity_docs_retrieval, get_model


class HybridRetriever:
    """BM25와 임베딩 검색을 결합한 하이브리드 검색기"""
    
    def __init__(self, 
                bm25_weight: float = 0.5,
                embedding_weight: float = 0.5,
                k1: float = 1.5,
                b: float = 0.75):
        """
        Args:
            bm25_weight: BM25 점수 가중치
            embedding_weight: 임베딩 점수 가중치
            k1: BM25 k1 매개변수
            b: BM25 b 매개변수
        """
        self.bm25_weight = bm25_weight
        self.embedding_weight = embedding_weight
        
        # 구성 요소 초기화
        self.bm25_retriever = BM25Retriever(k1=k1, b=b)
        self.query_processor = QueryProcessor()
        self.embedding_model = None
        self.document_embeddings = None
        
        # 점수 정규화를 위한 스케일러
        self.bm25_scaler = MinMaxScaler()
        self.embedding_scaler = MinMaxScaler()
        
        # 인덱스 구축 여부
        self.is_indexed = False
        self.documents = []
    
    def build_index(self, documents: List[str]) -> None:
        """하이브리드 인덱스 구축"""
        print("하이브리드 검색 인덱스 구축 시작...")
        
        self.documents = documents
        
        # 1. BM25 인덱스 구축
        print("1. BM25 인덱스 구축...")
        self.bm25_retriever.build_index(documents)
        
        # 2. 임베딩 모델 로드 및 문서 임베딩 계산
        print("2. 임베딩 모델 로드 및 문서 임베딩 계산...")
        self.embedding_model = get_model()
        self.document_embeddings = self.embedding_model.encode(documents, batch_size=2)
        
        print("하이브리드 검색 인덱스 구축 완료")
        self.is_indexed = True
    
    def _normalize_scores(self, scores: List[float], scaler: MinMaxScaler) -> np.ndarray:
        """점수 정규화 (0-1 범위)"""
        if not scores:
            return np.array([])
        
        scores_array = np.array(scores).reshape(-1, 1)
        
        # 모든 점수가 같은 경우 처리
        if np.std(scores_array) == 0:
            return np.ones(len(scores))
        
        try:
            normalized = scaler.fit_transform(scores_array).flatten()
            return normalized
        except:
            # 정규화 실패 시 원본 점수 반환
            return scores_array.flatten()
    
    def _combine_scores_weighted_average(self, 
                                        bm25_scores: np.ndarray, 
                                        embedding_scores: np.ndarray) -> np.ndarray:
        """가중 평균으로 점수 결합"""
        return (self.bm25_weight * bm25_scores + 
                self.embedding_weight * embedding_scores)
    
    def _combine_scores_rrf(self, 
                            bm25_results: List[Tuple[int, float]], 
                            embedding_results: List[Tuple[int, float]], 
                            k: int = 60) -> List[Tuple[int, float]]:
        """Reciprocal Rank Fusion (RRF)로 점수 결합"""
        # 문서별 RRF 점수 계산
        rrf_scores = {}
        
        # BM25 결과 처리
        for rank, (doc_idx, score) in enumerate(bm25_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1 / (k + rank + 1)
        
        # 임베딩 결과 처리
        for rank, (doc_idx, score) in enumerate(embedding_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + 1 / (k + rank + 1)
        
        # RRF 점수 기준 정렬
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_results
    
    def search(self, 
                query: str, 
                top_k: int = 10,
                combination_method: str = "weighted_average",
                use_query_expansion: bool = True) -> Tuple[List[str], List[float]]:
        """하이브리드 검색 수행"""
        if not self.is_indexed:
            raise ValueError("인덱스가 구축되지 않았습니다. build_index()를 먼저 호출하세요.")
        
        if not query.strip():
            return [], []
        
        # 쿼리 전처리 및 확장
        if use_query_expansion:
            expanded_query = self.query_processor.get_expanded_query_string(query)
            search_query = expanded_query if expanded_query.strip() else query
        else:
            search_query = query
        
        print(f"원본 쿼리: {query}")
        if use_query_expansion and search_query != query:
            print(f"확장된 쿼리: {search_query}")
        
        # 1. BM25 검색
        try:
            bm25_docs, bm25_scores = self.bm25_retriever.search(search_query, top_k=top_k*2)
        except Exception as e:
            print(f"BM25 검색 오류: {e}")
            bm25_docs, bm25_scores = [], []
        
        # 2. 임베딩 검색
        try:
            embedding_docs, embedding_scores = similarity_docs_retrieval(
                search_query, 
                self.documents, 
                precomputed_doc_embeddings=self.document_embeddings
            )
            # top_k*2 개로 제한
            embedding_docs = embedding_docs[:top_k*2]
            embedding_scores = embedding_scores[:top_k*2]
        except Exception as e:
            print(f"임베딩 검색 오류: {e}")
            embedding_docs, embedding_scores = [], []
        
        # 3. 결과 결합
        if combination_method == "weighted_average":
            return self._combine_weighted_average(
                bm25_docs, bm25_scores, 
                embedding_docs, embedding_scores, 
                top_k
            )
        elif combination_method == "rrf":
            return self._combine_rrf(
                bm25_docs, bm25_scores,
                embedding_docs, embedding_scores,
                top_k
            )
        else:
            raise ValueError(f"지원하지 않는 결합 방법: {combination_method}")
    
    def _combine_weighted_average(self, 
                                bm25_docs: List[str], 
                                bm25_scores: List[float],
                                embedding_docs: List[str], 
                                embedding_scores: List[float],
                                top_k: int) -> Tuple[List[str], List[float]]:
        """가중 평균 방식으로 결과 결합"""
        # 문서 인덱스 매핑
        doc_to_idx = {doc: idx for idx, doc in enumerate(self.documents)}
        
        # 각 검색 결과를 문서 인덱스와 점수로 변환
        bm25_results = {}
        for doc, score in zip(bm25_docs, bm25_scores):
            if doc in doc_to_idx:
                bm25_results[doc_to_idx[doc]] = score
        
        embedding_results = {}
        for doc, score in zip(embedding_docs, embedding_scores):
            if doc in doc_to_idx:
                embedding_results[doc_to_idx[doc]] = score
        
        # 모든 관련 문서 수집
        all_doc_indices = set(bm25_results.keys()) | set(embedding_results.keys())
        
        if not all_doc_indices:
            return [], []
        
        # 점수 정규화
        all_bm25_scores = [bm25_results.get(idx, 0) for idx in all_doc_indices]
        all_embedding_scores = [embedding_results.get(idx, 0) for idx in all_doc_indices]
        
        normalized_bm25 = self._normalize_scores(all_bm25_scores, self.bm25_scaler)
        normalized_embedding = self._normalize_scores(all_embedding_scores, self.embedding_scaler)
        
        # 가중 평균 계산
        combined_scores = self._combine_scores_weighted_average(normalized_bm25, normalized_embedding)
        
        # 결과 정렬 및 상위 k개 선택
        doc_score_pairs = list(zip(all_doc_indices, combined_scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        top_results = doc_score_pairs[:top_k]
        
        # 최종 결과 반환
        final_docs = [self.documents[doc_idx] for doc_idx, _ in top_results]
        final_scores = [score for _, score in top_results]
        
        return final_docs, final_scores
    
    def _combine_rrf(self,
                    bm25_docs: List[str], 
                    bm25_scores: List[float],
                    embedding_docs: List[str], 
                    embedding_scores: List[float],
                    top_k: int) -> Tuple[List[str], List[float]]:
        """RRF 방식으로 결과 결합"""
        doc_to_idx = {doc: idx for idx, doc in enumerate(self.documents)}
        
        # 순위 기반 결과 생성
        bm25_ranked = [(doc_to_idx[doc], score) for doc, score in zip(bm25_docs, bm25_scores) if doc in doc_to_idx]
        embedding_ranked = [(doc_to_idx[doc], score) for doc, score in zip(embedding_docs, embedding_scores) if doc in doc_to_idx]
        
        # RRF 점수 계산
        rrf_results = self._combine_scores_rrf(bm25_ranked, embedding_ranked)
        
        # 상위 k개 선택
        top_results = rrf_results[:top_k]
        
        # 최종 결과 반환
        final_docs = [self.documents[doc_idx] for doc_idx, _ in top_results]
        final_scores = [score for _, score in top_results]
        
        return final_docs, final_scores
    
    def set_weights(self, bm25_weight: float, embedding_weight: float) -> None:
        """검색 가중치 동적 조정"""
        total_weight = bm25_weight + embedding_weight
        if total_weight == 0:
            raise ValueError("가중치의 합이 0이 될 수 없습니다.")
        
        self.bm25_weight = bm25_weight / total_weight
        self.embedding_weight = embedding_weight / total_weight
        
        print(f"가중치 업데이트: BM25={self.bm25_weight:.2f}, Embedding={self.embedding_weight:.2f}")
    
    def get_component_results(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """각 구성 요소별 검색 결과 반환 (디버깅용)"""
        if not self.is_indexed:
            raise ValueError("인덱스가 구축되지 않았습니다.")
        
        # 쿼리 확장
        expanded_query = self.query_processor.get_expanded_query_string(query)
        
        # 각 구성 요소별 검색
        bm25_docs, bm25_scores = self.bm25_retriever.search(expanded_query, top_k)
        embedding_docs, embedding_scores = similarity_docs_retrieval(
            expanded_query, 
            self.documents, 
            precomputed_doc_embeddings=self.document_embeddings
        )
        # top_k 개로 제한
        embedding_docs = embedding_docs[:top_k]
        embedding_scores = embedding_scores[:top_k]
        
        return {
            "original_query": query,
            "expanded_query": expanded_query,
            "bm25_results": {
                "documents": bm25_docs,
                "scores": bm25_scores
            },
            "embedding_results": {
                "documents": embedding_docs,
                "scores": embedding_scores
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """검색기 통계 정보 반환"""
        stats = {
            "is_indexed": self.is_indexed,
            "num_documents": len(self.documents),
            "weights": {
                "bm25": self.bm25_weight,
                "embedding": self.embedding_weight
            }
        }
        
        if self.is_indexed:
            stats["bm25_stats"] = self.bm25_retriever.get_index_statistics()
            stats["embedding_model"] = type(self.embedding_model).__name__ if self.embedding_model else None
        
        return stats
