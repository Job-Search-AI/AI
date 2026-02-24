from typing import Any, TypedDict


class ModelCacheState(TypedDict, total=False):
    bert_model_name: str
    device: str | None
    bert_model: Any
    tokenizer: Any
    crf: Any
    embedding_model: Any
    llm: Any
