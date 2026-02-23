from .tools import DEFAULT_BERT_MODEL_NAME, ensure_model_cache


def singleton_model_node(state: dict) -> dict:
    if isinstance(state, dict):
        bert_model_name = state.get("bert_model_name", DEFAULT_BERT_MODEL_NAME)
    else:
        bert_model_name = DEFAULT_BERT_MODEL_NAME

    if not isinstance(bert_model_name, str) or not bert_model_name.strip():
        bert_model_name = DEFAULT_BERT_MODEL_NAME

    return ensure_model_cache(bert_model_name)
