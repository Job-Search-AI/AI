from typing import Any, TypedDict


class RetrievalOptionState(TypedDict, total=False):
    # 검색 노드에서 사용할 옵션을 분리해 state 계약을 명확히 유지한다.
    retrieval_top_k: int
    retrieval_combination_method: str
    retrieval_use_query_expansion: bool
    retrieval_bm25_weight: float
    retrieval_embedding_weight: float


class RetrievalState(TypedDict, total=False):
    # 입력/캐시/결과를 한 타입에 모아 노드 입출력 타입 힌트를 단순화한다.
    query: str
    job_info_list: list[str]
    retriever: Any
    retrieval_top_k: int
    retrieval_combination_method: str
    retrieval_use_query_expansion: bool
    retrieval_bm25_weight: float
    retrieval_embedding_weight: float
    retrieved_job_info_list: list[str]
    retrieved_scores: list[float]
