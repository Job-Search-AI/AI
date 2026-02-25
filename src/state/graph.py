from typing import TypedDict

from .slices import EntitySlots, NormalizedEntitySlots


class GraphState(TypedDict, total=False):
    # user input / session
    user_input: str
    follow_up_input: str
    query: str
    conversation_id: str

    # model cache
    bert_model_name: str
    device: str | None
    bert_model: object
    tokenizer: object
    crf: object
    embedding_model: object
    llm: object

    # NER / normalization
    entities: EntitySlots
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None
    status: str
    message: str | None
    missing_fields: list[str] | None
    normalized_entities: NormalizedEntitySlots

    # url/crawling/parsing
    url: str
    max_jobs: int
    html_contents: list[str]
    crawled_count: int
    job_info_list: list[str]
    job_metadata_list: list[dict[str, object]]

    # retrieval
    # 검색 옵션 키를 state에 고정해 노드가 dict 키 문자열에 의존하지 않게 한다.
    retriever: object
    precomputed_doc_embeddings: object
    retrieval_top_k: int
    retrieval_combination_method: str
    retrieval_use_query_expansion: bool
    retrieval_bm25_weight: float
    retrieval_embedding_weight: float
    retrieved_job_info_list: list[str]
    retrieved_scores: list[float]

    # llm output
    user_response: str

    # pipeline status
    error: str | None
