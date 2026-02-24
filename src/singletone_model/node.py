from src.state import GraphState, SingletonModelNodeUpdate

from .tools import DEFAULT_BERT_MODEL_NAME, ensure_model_cache


def singleton_model_node(state: GraphState) -> SingletonModelNodeUpdate:
    bert_model_name = state.get("bert_model_name", DEFAULT_BERT_MODEL_NAME)

    if not isinstance(bert_model_name, str) or not bert_model_name.strip():
        bert_model_name = DEFAULT_BERT_MODEL_NAME

    cache = ensure_model_cache(bert_model_name)
    update: SingletonModelNodeUpdate = {
        "bert_model_name": bert_model_name,
        "device": cache.get("device"),
        "bert_model": cache.get("bert_model"),
        "tokenizer": cache.get("tokenizer"),
        "crf": cache.get("crf"),
        "embedding_model": cache.get("embedding_model"),
        "llm": cache.get("llm"),
    }
    return update
