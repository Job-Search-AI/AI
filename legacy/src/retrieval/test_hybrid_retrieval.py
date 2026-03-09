"""
하이브리드 검색 시스템 테스트 스크립트
"""

import sys
import json
import time
import torch

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from src.retrieval.hybrid_retriever import (
    build_hybrid_retriever,
    get_hybrid_component_results,
    get_hybrid_statistics,
    search_hybrid_retriever,
)
# 레거시 테스트 스크립트는 분리된 evaluation metrics를 직접 참조하도록 경로를 맞춘다.
from legacy.src.evaluation.retrieval.metrics import recall_at_k, precision_at_k, hit_at_k
from collections import defaultdict


def load_jsonl(path: str):
    """JSONL 파일 로드"""
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def docs_to_strings(docs):
    """문서를 문자열로 변환"""
    strings = []
    for d in docs:
        if isinstance(d, dict) and 'data' in d and isinstance(d['data'], str):
            strings.append(d['data'])
        else:
            strings.append(json.dumps(d, ensure_ascii=False))
    return strings


def test_hybrid_retrieval():
    """하이브리드 검색 시스템 테스트"""
    print("=== 하이브리드 검색 시스템 테스트 ===")
    
    # 데이터 로드
    print("1. 데이터 로드...")
    job_data_file = '/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/data.jsonl'
    ground_truth_file = '/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/ground_truth.json'
    
    job_data = load_jsonl(job_data_file)
    job_data_strings = docs_to_strings(job_data)
    
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_list = json.load(f)
    
    print(f"문서 수: {len(job_data_strings)}")
    print(f"테스트 쿼리 수: {len(ground_truth_list)}")
    
    # 하이브리드 검색기 초기화 및 인덱스 구축
    print("\n2. 하이브리드 검색기 초기화...")
    start_time = time.time()
    retriever_context = build_hybrid_retriever(
        job_data_strings,
        bm25_weight=0.4,
        embedding_weight=0.6,
    )
    index_time = time.time() - start_time
    print(f"인덱스 구축 시간: {index_time:.2f}초")
    
    # 검색기 통계 출력
    stats = get_hybrid_statistics(retriever_context)
    print(f"\n검색기 통계:")
    print(f"- 문서 수: {stats['num_documents']}")
    print(f"- BM25 가중치: {stats['weights']['bm25']:.2f}")
    print(f"- 임베딩 가중치: {stats['weights']['embedding']:.2f}")
    
    # 문서 인덱스 매핑 구축
    inverted_index = defaultdict(list)
    for idx, doc_str in enumerate(job_data_strings):
        inverted_index[doc_str].append(idx)
    
    # 평가 수행
    print("\n3. 성능 평가 수행...")
    k_values = [1, 3, 5, 10]
    all_results = {"per_query": {}, "macro_avg": {}}
    agg = {k: {"recall": 0.0, "precision": 0.0, "hit": 0.0} for k in k_values}
    n_queries = 0
    
    for item in ground_truth_list:
        query = item.get("query", "").strip()
        relevant_indices = item.get("relevant_doc_indices", [])
        
        if not query:
            continue
        
        print(f"\n쿼리: {query}")
        
        # 정답 인덱스 처리 (1-based -> 0-based 변환)
        n_docs = len(job_data_strings)
        raw_indices = [idx for idx in relevant_indices if isinstance(idx, int)]
        
        if raw_indices and 0 not in raw_indices and max(raw_indices) <= n_docs:
            adjusted = [idx - 1 for idx in raw_indices]
        else:
            adjusted = raw_indices
        
        filtered_relevant = [idx for idx in adjusted if 0 <= idx < n_docs]
        relevant_indices = filtered_relevant
        
        print(f"정답 문서 인덱스: {relevant_indices}")
        
        # 하이브리드 검색 수행
        start_time = time.time()
        retrieved_docs, scores = search_hybrid_retriever(
            retriever_context,
            query, 
            top_k=10, 
            combination_method="weighted_average",
            use_query_expansion=True
        )
        search_time = time.time() - start_time
        
        print(f"검색 시간: {search_time:.3f}초")
        
        # 검색된 문서 -> 인덱스 변환
        retrieved_indices = []
        for doc in retrieved_docs:
            if doc in inverted_index and inverted_index[doc]:
                retrieved_indices.append(inverted_index[doc].pop(0))
        
        # 인덱스 복원 (다음 쿼리를 위해)
        for idx, doc_str in enumerate(job_data_strings):
            inverted_index[doc_str] = [idx]
        
        print(f"검색된 문서 인덱스 (상위 10개): {retrieved_indices[:10]}")
        
        # 메트릭 계산
        per_k = {}
        for k in k_values:
            recall = recall_at_k(retrieved_indices, relevant_indices, k)
            precision = precision_at_k(retrieved_indices, relevant_indices, k)
            hit = hit_at_k(retrieved_indices, relevant_indices, k)
            
            per_k[k] = {"recall": recall, "precision": precision, "hit": hit}
            
            agg[k]["recall"] += recall
            agg[k]["precision"] += precision
            agg[k]["hit"] += hit
            
            print(f"  k={k} | Recall@{k}: {recall:.4f} | Precision@{k}: {precision:.4f} | Hit@{k}: {hit:.4f}")
        
        all_results["per_query"][query] = per_k
        n_queries += 1
        
        # GPU 메모리 정리
        torch.cuda.empty_cache()
    
    # 매크로 평균 계산
    if n_queries > 0:
        for k in k_values:
            all_results["macro_avg"][k] = {
                "recall": agg[k]["recall"] / n_queries,
                "precision": agg[k]["precision"] / n_queries,
                "hit": agg[k]["hit"] / n_queries,
            }
    
    return all_results


def compare_methods():
    """다양한 검색 방법 비교"""
    print("\n=== 검색 방법 비교 ===")
    
    # 데이터 로드
    job_data_file = '/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/data.jsonl'
    job_data = load_jsonl(job_data_file)
    job_data_strings = docs_to_strings(job_data)
    
    # 하이브리드 검색기 초기화
    retriever_context = build_hybrid_retriever(job_data_strings)
    
    # 테스트 쿼리
    test_queries = [
        "서울 신입 4년제대졸 NLP 개발자",
        "서울 신입 대졸 AI 연구원",
        "서울 무관 대졸 데이터사이언티스트"
    ]
    
    for query in test_queries:
        print(f"\n쿼리: {query}")
        print("-" * 50)
        
        # 구성 요소별 결과 확인
        component_results = get_hybrid_component_results(
            retriever_context,
            query,
            top_k=5,
        )
        
        print(f"확장된 쿼리: {component_results['expanded_query']}")
        
        print("\nBM25 상위 5개 결과:")
        for i, (doc, score) in enumerate(zip(component_results['bm25_results']['documents'], 
                                           component_results['bm25_results']['scores'])):
            print(f"  {i+1}. (점수: {score:.4f}) {doc[:100]}...")
        
        print("\n임베딩 상위 5개 결과:")
        for i, (doc, score) in enumerate(zip(component_results['embedding_results']['documents'], 
                                           component_results['embedding_results']['scores'])):
            print(f"  {i+1}. (점수: {score:.4f}) {doc[:100]}...")
        
        # 하이브리드 결과
        hybrid_docs, hybrid_scores = search_hybrid_retriever(
            retriever_context,
            query,
            top_k=5,
        )
        print("\n하이브리드 상위 5개 결과:")
        for i, (doc, score) in enumerate(zip(hybrid_docs, hybrid_scores)):
            print(f"  {i+1}. (점수: {score:.4f}) {doc[:100]}...")


if __name__ == "__main__":
    # 하이브리드 검색 시스템 테스트
    results = test_hybrid_retrieval()
    
    print("\n=== 최종 성능 결과 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # 검색 방법 비교
    compare_methods()
    
    print("\n=== 테스트 완료 ===")
