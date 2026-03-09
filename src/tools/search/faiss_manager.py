"""
FAISS 벡터 인덱스 관리 시스템
"""

import faiss
import numpy as np
import pickle
import os
import time
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
import json
import sys

# 프로젝트 경로 추가
sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")


@dataclass
class IndexConfig:
    """인덱스 설정 클래스"""
    index_type: str  # "flat", "ivf", "hnsw"
    dimension: int
    
    # IVF 설정
    nlist: int = 100  # 클러스터 수
    nprobe: int = 10  # 검색할 클러스터 수
    
    # HNSW 설정
    M: int = 16  # 연결 수
    efConstruction: int = 200  # 구축 시 탐색 범위
    efSearch: int = 50  # 검색 시 탐색 범위
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_type": self.index_type,
            "dimension": self.dimension,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
            "M": self.M,
            "efConstruction": self.efConstruction,
            "efSearch": self.efSearch
        }


class FAISSIndexManager:
    """FAISS 인덱스 관리 클래스"""
    
    def __init__(self, config: IndexConfig):
        """
        Args:
            config: 인덱스 설정
        """
        self.config = config
        self.index = None
        self.document_ids = []  # 문서 ID 매핑
        self.is_trained = False
        
        self._create_index()
    
    def _create_index(self):
        """설정에 따른 인덱스 생성"""
        dimension = self.config.dimension
        
        if self.config.index_type == "flat":
            # 정확한 검색 (브루트 포스)
            self.index = faiss.IndexFlatIP(dimension)
            self.is_trained = True
            
        elif self.config.index_type == "ivf":
            # IVF (Inverted File) - 클러스터 기반 근사 검색
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, self.config.nlist)
            self.index.nprobe = self.config.nprobe
            
        elif self.config.index_type == "hnsw":
            # HNSW (Hierarchical Navigable Small World) - 그래프 기반
            self.index = faiss.IndexHNSWFlat(dimension, self.config.M)
            self.index.hnsw.efConstruction = self.config.efConstruction
            self.index.hnsw.efSearch = self.config.efSearch
            self.is_trained = True
            
        else:
            raise ValueError(f"지원하지 않는 인덱스 타입: {self.config.index_type}")
        
        print(f"{self.config.index_type.upper()} 인덱스 생성 완료 (차원: {dimension})")
    
    def train_index(self, vectors: np.ndarray):
        """인덱스 훈련 (IVF 타입에서 필요)"""
        if self.config.index_type == "ivf" and not self.is_trained:
            print(f"IVF 인덱스 훈련 시작... (벡터 수: {len(vectors)})")
            start_time = time.time()
            
            # 벡터를 float32로 변환
            vectors = vectors.astype('float32')
            
            # 훈련
            self.index.train(vectors)
            self.is_trained = True
            
            train_time = time.time() - start_time
            print(f"IVF 인덱스 훈련 완료 (소요 시간: {train_time:.2f}초)")
    
    def add_vectors(self, vectors: np.ndarray, document_ids: List[str] = None):
        """
        벡터 추가
        
        Args:
            vectors: 추가할 벡터 배열 (N, dimension)
            document_ids: 문서 ID 리스트 (선택사항)
        """
        if not self.is_trained:
            self.train_index(vectors)
        
        # 벡터를 float32로 변환
        vectors = vectors.astype('float32')
        
        # 문서 ID 관리
        if document_ids is None:
            document_ids = [f"doc_{len(self.document_ids) + i}" for i in range(len(vectors))]
        
        if len(document_ids) != len(vectors):
            raise ValueError("document_ids와 vectors의 길이가 일치하지 않습니다.")
        
        print(f"벡터 추가 중... (개수: {len(vectors)})")
        start_time = time.time()
        
        # 인덱스에 벡터 추가
        self.index.add(vectors)
        self.document_ids.extend(document_ids)
        
        add_time = time.time() - start_time
        print(f"벡터 추가 완료 (소요 시간: {add_time:.2f}초)")
        print(f"총 인덱스 크기: {self.index.ntotal}")
    
    def search(self, query_vectors: np.ndarray, k: int = 10) -> Tuple[np.ndarray, List[List[str]]]:
        """
        벡터 검색
        
        Args:
            query_vectors: 쿼리 벡터 배열 (N, dimension)
            k: 반환할 결과 수
            
        Returns:
            Tuple[distances, document_ids]: 거리 점수와 문서 ID 리스트
        """
        if self.index.ntotal == 0:
            raise ValueError("인덱스가 비어있습니다. 먼저 벡터를 추가해주세요.")
        
        # 벡터를 float32로 변환
        query_vectors = query_vectors.astype('float32')
        
        start_time = time.time()
        
        # 검색 실행
        distances, indices = self.index.search(query_vectors, k)
        
        search_time = time.time() - start_time
        
        # 인덱스를 문서 ID로 변환
        result_document_ids = []
        for query_indices in indices:
            query_doc_ids = []
            for idx in query_indices:
                if idx >= 0 and idx < len(self.document_ids):
                    query_doc_ids.append(self.document_ids[idx])
                else:
                    query_doc_ids.append(None)  # 유효하지 않은 인덱스
            result_document_ids.append(query_doc_ids)
        
        print(f"검색 완료 (소요 시간: {search_time:.4f}초, 쿼리 수: {len(query_vectors)})")
        
        return distances, result_document_ids
    
    def get_index_info(self) -> Dict[str, Any]:
        """인덱스 정보 반환"""
        return {
            "config": self.config.to_dict(),
            "total_vectors": self.index.ntotal if self.index else 0,
            "is_trained": self.is_trained,
            "document_count": len(self.document_ids)
        }
    
    def save_index(self, filepath: str):
        """인덱스 저장"""
        if self.index is None:
            raise ValueError("저장할 인덱스가 없습니다.")
        
        # 인덱스 파일 저장
        faiss.write_index(self.index, f"{filepath}.index")
        
        # 메타데이터 저장
        metadata = {
            "config": self.config.to_dict(),
            "document_ids": self.document_ids,
            "is_trained": self.is_trained
        }
        
        with open(f"{filepath}.metadata", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"인덱스 저장 완료: {filepath}")
    
    def load_index(self, filepath: str):
        """인덱스 로드"""
        # 인덱스 파일 로드
        if not os.path.exists(f"{filepath}.index"):
            raise FileNotFoundError(f"인덱스 파일을 찾을 수 없습니다: {filepath}.index")
        
        self.index = faiss.read_index(f"{filepath}.index")
        
        # 메타데이터 로드
        if os.path.exists(f"{filepath}.metadata"):
            with open(f"{filepath}.metadata", 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 설정 복원
            config_dict = metadata.get("config", {})
            self.config = IndexConfig(**config_dict)
            
            # 문서 ID 복원
            self.document_ids = metadata.get("document_ids", [])
            self.is_trained = metadata.get("is_trained", True)
        
        print(f"인덱스 로드 완료: {filepath}")
        print(f"총 벡터 수: {self.index.ntotal}")
    
    def remove_vectors(self, document_ids_to_remove: List[str]):
        """
        특정 문서 벡터 제거 (재구축 방식)
        
        Args:
            document_ids_to_remove: 제거할 문서 ID 리스트
        """
        # FAISS는 직접적인 벡터 제거를 지원하지 않으므로 재구축 필요
        print("벡터 제거를 위해 인덱스를 재구축합니다...")
        
        # 제거할 인덱스 찾기
        indices_to_remove = set()
        for doc_id in document_ids_to_remove:
            if doc_id in self.document_ids:
                indices_to_remove.add(self.document_ids.index(doc_id))
        
        if not indices_to_remove:
            print("제거할 벡터가 없습니다.")
            return
        
        # 기존 벡터 추출 (FAISS에서 직접 추출은 불가능하므로 별도 저장 필요)
        print(f"주의: 벡터 제거 기능을 사용하려면 원본 벡터를 별도로 저장해야 합니다.")
        print(f"현재는 문서 ID 리스트만 업데이트됩니다.")
        
        # 문서 ID 리스트에서 제거
        self.document_ids = [
            doc_id for i, doc_id in enumerate(self.document_ids) 
            if i not in indices_to_remove
        ]
        
        print(f"문서 ID {len(indices_to_remove)}개 제거 완료")


class FAISSBenchmark:
    """FAISS 성능 벤치마크 클래스"""
    
    def __init__(self):
        self.results = []
    
    def benchmark_index_types(self, vectors: np.ndarray, query_vectors: np.ndarray, 
                            k: int = 10) -> Dict[str, Dict[str, Any]]:
        """
        다양한 인덱스 타입 성능 비교
        
        Args:
            vectors: 인덱싱할 벡터
            query_vectors: 쿼리 벡터
            k: 검색할 결과 수
            
        Returns:
            Dict: 인덱스 타입별 성능 결과
        """
        dimension = vectors.shape[1]
        results = {}
        
        # 테스트할 인덱스 타입들
        index_configs = [
            IndexConfig("flat", dimension),
            IndexConfig("ivf", dimension, nlist=min(100, len(vectors)//10)),
            IndexConfig("hnsw", dimension, M=16)
        ]
        
        for config in index_configs:
            print(f"\n=== {config.index_type.upper()} 인덱스 벤치마크 ===")
            
            try:
                # 인덱스 생성 및 벡터 추가
                manager = FAISSIndexManager(config)
                
                # 인덱스 구축 시간 측정
                build_start = time.time()
                manager.add_vectors(vectors)
                build_time = time.time() - build_start
                
                # 검색 시간 측정
                search_start = time.time()
                distances, doc_ids = manager.search(query_vectors, k)
                search_time = time.time() - search_start
                
                # 메모리 사용량 (근사치)
                memory_usage = self._estimate_memory_usage(manager.index)
                
                # 결과 저장
                results[config.index_type] = {
                    "build_time": build_time,
                    "search_time": search_time,
                    "queries_per_second": len(query_vectors) / search_time,
                    "memory_usage_mb": memory_usage,
                    "config": config.to_dict(),
                    "distances": distances.tolist(),
                    "document_ids": doc_ids
                }
                
                print(f"구축 시간: {build_time:.4f}초")
                print(f"검색 시간: {search_time:.4f}초")
                print(f"QPS: {len(query_vectors) / search_time:.2f}")
                print(f"메모리 사용량: {memory_usage:.2f}MB")
                
            except Exception as e:
                print(f"{config.index_type} 벤치마크 실패: {e}")
                results[config.index_type] = {"error": str(e)}
        
        return results
    
    def _estimate_memory_usage(self, index) -> float:
        """메모리 사용량 추정 (MB)"""
        try:
            # FAISS 인덱스의 대략적인 메모리 사용량 계산
            if hasattr(index, 'ntotal') and hasattr(index, 'd'):
                # 벡터 수 * 차원 * 4바이트 (float32)
                vector_memory = index.ntotal * index.d * 4
                
                # 인덱스 오버헤드 (타입에 따라 다름)
                if "IVF" in str(type(index)):
                    overhead = vector_memory * 0.1  # IVF 오버헤드 약 10%
                elif "HNSW" in str(type(index)):
                    overhead = vector_memory * 0.5  # HNSW 오버헤드 약 50%
                else:
                    overhead = 0
                
                total_bytes = vector_memory + overhead
                return total_bytes / (1024 * 1024)  # MB로 변환
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def save_benchmark_results(self, results: Dict[str, Any], filepath: str):
        """벤치마크 결과 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"벤치마크 결과 저장: {filepath}")


def test_faiss_manager():
    """테스트 함수"""
    print("=== FAISS Manager 테스트 ===")
    
    # 테스트 데이터 생성
    dimension = 384  # 일반적인 임베딩 차원
    num_vectors = 1000
    num_queries = 10
    
    # 랜덤 벡터 생성
    np.random.seed(42)
    vectors = np.random.random((num_vectors, dimension)).astype('float32')
    query_vectors = np.random.random((num_queries, dimension)).astype('float32')
    
    # 문서 ID 생성
    document_ids = [f"job_{i:04d}" for i in range(num_vectors)]
    
    # 1. Flat 인덱스 테스트
    print("\n--- Flat 인덱스 테스트 ---")
    config = IndexConfig("flat", dimension)
    manager = FAISSIndexManager(config)
    manager.add_vectors(vectors, document_ids)
    
    distances, doc_ids = manager.search(query_vectors, k=5)
    print(f"검색 결과 (첫 번째 쿼리): {doc_ids[0]}")
    
    # 2. 인덱스 저장/로드 테스트
    print("\n--- 저장/로드 테스트 ---")
    save_path = "/tmp/test_index"
    manager.save_index(save_path)
    
    # 새 매니저로 로드
    new_manager = FAISSIndexManager(IndexConfig("flat", dimension))
    new_manager.load_index(save_path)
    
    # 동일한 결과 확인
    new_distances, new_doc_ids = new_manager.search(query_vectors, k=5)
    print(f"로드 후 검색 결과: {new_doc_ids[0]}")
    print(f"결과 일치: {doc_ids[0] == new_doc_ids[0]}")
    
    # 3. 벤치마크 테스트
    print("\n--- 벤치마크 테스트 ---")
    benchmark = FAISSBenchmark()
    results = benchmark.benchmark_index_types(vectors[:100], query_vectors[:5], k=10)
    
    print("\n=== 벤치마크 결과 요약 ===")
    for index_type, result in results.items():
        if "error" not in result:
            print(f"{index_type}: {result['queries_per_second']:.2f} QPS, "
                  f"{result['memory_usage_mb']:.2f}MB")


if __name__ == "__main__":
    test_faiss_manager()
