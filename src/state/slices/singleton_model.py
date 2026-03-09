from typing import Any, Callable, TypedDict


class SingletonModelCache(TypedDict):
    device: str | None
    bert_model: Any | None
    tokenizer: Any | None
    crf: Any | None
    embedding_model: Any | None
    llm: Callable[..., Any] | None


def _create_empty_model_cache() -> SingletonModelCache:
    return {
        "device": None,
        "bert_model": None,
        "tokenizer": None,
        "crf": None,
        "embedding_model": None,
        "llm": None,
    }


_MODEL_CACHE: SingletonModelCache = _create_empty_model_cache()


def get_model_cache() -> SingletonModelCache:
    return _MODEL_CACHE


def reset_model_cache() -> None:
    global _MODEL_CACHE
    _MODEL_CACHE = _create_empty_model_cache()


class SingletonModelNodeState(TypedDict, total=False):
    bert_model_name: str


class SingletonModelNodeUpdate(TypedDict):
    bert_model_name: str
    device: str | None
    bert_model: Any | None
    tokenizer: Any | None
    crf: Any | None
    embedding_model: Any | None
    llm: Callable[..., Any] | None
