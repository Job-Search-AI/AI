import sys
import json
import os

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from config import EVAL_URL
from src.crawling.job_crawler import crawl_job_html_from_saramin
from src.embedding.model import similarity_docs_retrieval
from src.evaluation.retrieval.metrics import recall_at_k, precision_at_k, hit_at_k
from src.parsing.main import parsing_job_info
from bs4 import BeautifulSoup
import re

def save_evaluation_data(job_data, relevant_indices, query="NLP ai 엔지니어 서울 고졸 신입 공고만 가져와줘"):
    """평가용 데이터를 data 폴더에 저장"""
    print("평가용 데이터 저장 시작")
    
    # data/eval 폴더 생성
    eval_dir = "/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval"
    os.makedirs(eval_dir, exist_ok=True)
    
    # 전체 40개 데이터 저장
    job_data_file = os.path.join(eval_dir, "job_data_40.json")
    with open(job_data_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, ensure_ascii=False, indent=2)
    print(f"40개 평가용 데이터 저장 완료: {job_data_file}")
    
    # 정답 데이터 (쿼리와 관련 문서 인덱스) 저장
    ground_truth = {
        "query": query,
        "relevant_doc_indices": relevant_indices,
        "total_docs": len(job_data)
    }
    
    ground_truth_file = os.path.join(eval_dir, "ground_truth.json")
    with open(ground_truth_file, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)
    print(f"정답 데이터 저장 완료: {ground_truth_file}")
    
    print(f"저장된 정답 문서 인덱스: {relevant_indices}")
    
    return job_data_file, ground_truth_file

def evaluate_retriever_with_real_data():
    """실제 데이터로 리트리버 평가"""
    print("실제 데이터로 리트리버 평가 시작")
    
    # 저장된 데이터 로드
    eval_dir = "/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval"
    
    # 40개 평가용 데이터 로드
    job_data_file = os.path.join(eval_dir, "job_data_40.json")
    with open(job_data_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    # 정답 데이터 로드
    ground_truth_file = os.path.join(eval_dir, "ground_truth.json")
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    query = ground_truth["query"]
    relevant_indices = ground_truth["relevant_doc_indices"]
    
    print(f"쿼리: {query}")
    print(f"정답 문서 인덱스: {relevant_indices}")
    
    # 리트리버로 검색 수행 (문서를 문자열로 변환해서 전달)
    from src.utils import dict_to_str
    job_data_strings = dict_to_str(job_data)
    retrieved_docs, scores = similarity_docs_retrieval(query, job_data_strings)
    
    # 검색된 문서의 인덱스 찾기
    retrieved_indices = []
    for retrieved_doc in retrieved_docs:
        for i, job_string in enumerate(job_data_strings):
            if job_string == retrieved_doc:
                retrieved_indices.append(i)
                break
    
    print(f"검색된 문서 인덱스 (상위 10개): {retrieved_indices[:10]}")
    
    # 메트릭 계산
    k_values = [1, 3, 5, 10]
    results = {}
    
    for k in k_values:
        recall = recall_at_k(retrieved_indices, relevant_indices, k)
        precision = precision_at_k(retrieved_indices, relevant_indices, k)
        hit = hit_at_k(retrieved_indices, relevant_indices, k)
        
        results[k] = {
            "recall": recall,
            "precision": precision,
            "hit": hit
        }
        
        print(f"\nk={k}:")
        print(f"  Recall@{k}: {recall:.4f}")
        print(f"  Precision@{k}: {precision:.4f}")
        print(f"  Hit@{k}: {hit:.4f}")
    
    return results

if __name__ == "__main__":


    # # 데이터 크롤링
    # query = "NLP ai 엔지니어 서울 고졸 신입 공고만 가져와줘"
    # job_data = crawl_job_html_from_saramin(EVAL_URL, 40)
    # parsed_job_data = parsing_job_info(job_data)
    
    # print("평가용 데이터 저장")
    # save_evaluation_data(parsed_job_data, relevant_indices)
    
    print("실제 데이터로 리트리버 평가")
    real_results = evaluate_retriever_with_real_data()

