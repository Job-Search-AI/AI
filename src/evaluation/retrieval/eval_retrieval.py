import sys
import json
import os

sys.path.append("/content/drive/MyDrive/ai_enginner/job_search/AI/")

from src.embedding.model import similarity_docs_retrieval
from src.evaluation.retrieval.metrics import recall_at_k, precision_at_k, hit_at_k

from collections import defaultdict, deque
from typing import List, Dict, Any

def evaluate_retriever_with_real_data():
    print("실제 데이터로 리트리버 평가 시작")

    # 데이터 경로
    job_data_file = '/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/data.jsonl'
    ground_truth_file = '/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/ground_truth.json'

    # JSONL 로드 유틸
    def load_jsonl(path: str) -> List[Dict[str, Any]]:
        items = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    # 일부 라인에 잘못된 문자가 있을 경우 무시
                    continue
        return items

    # 문서 문자열 변환 유틸
    def docs_to_strings(docs: List[Dict[str, Any]]) -> List[str]:
        strings: List[str] = []
        for d in docs:
            if isinstance(d, dict) and 'data' in d and isinstance(d['data'], str):
                strings.append(d['data'])
            else:
                strings.append(json.dumps(d, ensure_ascii=False))
        return strings

    # 1) 평가용 데이터 로드 (JSONL)
    job_data = load_jsonl(job_data_file)
    job_data_strings = docs_to_strings(job_data)

    # 중복 문자열도 안전하게 인덱싱할 수 있도록 역색인 구성
    inverted_index: Dict[str, deque] = defaultdict(deque)
    for idx, s in enumerate(job_data_strings):
        inverted_index[s].append(idx)

    # 2) 정답 데이터 로드 (여러 쿼리)
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_list = json.load(f)

    # 메트릭 설정
    k_values = [1, 3, 5, 10]
    all_results: Dict[str, Any] = {"per_query": {}, "macro_avg": {}}

    # 매크로 평균 집계용 버퍼
    agg = {k: {"recall": 0.0, "precision": 0.0, "hit": 0.0} for k in k_values}
    n_queries = 0

    # 각 쿼리에 대해 평가 수행
    for item in ground_truth_list:
        query = item.get("query", "").strip()
        relevant_indices = item.get("relevant_doc_indices", [])
        if not query:
            continue

        print(f"\n쿼리: {query}")
        # 정답 인덱스 유효성 검사 및 정제 (1-based -> 0-based 자동 보정 시도)
        n_docs = len(job_data_strings)
        raw_indices = [idx for idx in relevant_indices if isinstance(idx, int)]
        # 1-based로 작성되었을 가능성 판단: 0이 없고, 최대값이 문서 수 이하인 경우
        if raw_indices and 0 not in raw_indices and max(raw_indices) <= n_docs:
            adjusted = [idx - 1 for idx in raw_indices]
            print("참고: 정답 인덱스가 1-based로 작성된 것으로 판단되어 0-based로 변환했습니다.")
        else:
            adjusted = raw_indices
        filtered_relevant = [idx for idx in adjusted if 0 <= idx < n_docs]
        if len(filtered_relevant) != len(adjusted):
            print(f"경고: 일부 정답 인덱스가 유효 범위를 벗어나 제외되었습니다. 총 {len(adjusted)}개 -> 유효 {len(filtered_relevant)}개 (문서 수: {n_docs})")
        relevant_indices = filtered_relevant
        print(f"정답 문서 인덱스: {relevant_indices}")

        # 리트리버 검색
        retrieved_docs, scores = similarity_docs_retrieval(query, job_data_strings)

        # 검색된 문서 -> 인덱스 변환 (중복 안전)
        temp_inv = {k: deque(v) for k, v in inverted_index.items()}  # 쿼리별 독립적인 사용
        retrieved_indices: List[int] = []
        for doc in retrieved_docs:
            if doc in temp_inv and temp_inv[doc]:
                retrieved_indices.append(temp_inv[doc].popleft())
            else:
                # 매칭 실패 시 스킵
                continue

        if not retrieved_indices:
            print("검색 결과가 비어 있습니다.")
        else:
            print(f"검색된 문서 인덱스 (상위 10개): {retrieved_indices[:10]}")

        # 메트릭 계산
        per_k = {}
        for k in k_values:
            recall = recall_at_k(retrieved_indices, relevant_indices, k)
            precision = precision_at_k(retrieved_indices, relevant_indices, k)
            hit = hit_at_k(retrieved_indices, relevant_indices, k)

            per_k[k] = {"recall": recall, "precision": precision, "hit": hit}

            # 집계
            agg[k]["recall"] += recall
            agg[k]["precision"] += precision
            agg[k]["hit"] += hit

            print(f"  k={k} | Recall@{k}: {recall:.4f} | Precision@{k}: {precision:.4f} | Hit@{k}: {hit:.4f}")

        all_results["per_query"][query] = per_k
        n_queries += 1

    # 매크로 평균 계산
    if n_queries > 0:
        for k in k_values:
            all_results["macro_avg"][k] = {
                "recall": agg[k]["recall"] / n_queries,
                "precision": agg[k]["precision"] / n_queries,
                "hit": agg[k]["hit"] / n_queries,
            }

    return all_results

if __name__ == "__main__":
    print("실제 데이터로 리트리버 평가")
    real_results = evaluate_retriever_with_real_data()
    # 보기 좋게 출력
    print(json.dumps(real_results, ensure_ascii=False, indent=2))
