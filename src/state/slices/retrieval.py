from typing import Any, TypedDict


class RetrievalState(TypedDict, total=False):
    retriever: Any
    retrieved_job_info_list: list[str]
    retrieved_scores: list[float]
