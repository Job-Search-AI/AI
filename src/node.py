import os

from src.state import (
    CrawlingState,
    GraphState,
    NormalizeAndValidateEntitiesResultState,
    NormalizeAndValidateEntitiesState,
    NormalizeEntityInputState,
    PredictCrfBertResultState,
    RetrievalState,
    SingletonModelNodeUpdate,
)
from src.tools.slices.crawling import crawl_job_html_from_saramin as _crawl_job_html_from_saramin_tool
from src.tools.slices.retrieval import (
    build_hybrid_retriever as _build_hybrid_retriever_tool,
    search_hybrid_retriever as _search_hybrid_retriever_tool,
)
from src.tools.slices.llm import generate_response
from src.tools.slices.singleton_model import DEFAULT_BERT_MODEL_NAME, ensure_model_cache
from src.tools.slices.entity_normalizer import (
    check_missing_entities,
    generate_missing_message,
    normalize_entities,
)
from src.utils import dict_to_str


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


def predict_crf_bert(state: GraphState) -> PredictCrfBertResultState:
    import torch

    sentence = state.get("user_input")
    model = state.get("bert_model")
    crf = state.get("crf")
    tokenizer = state.get("tokenizer")
    device = state.get("device")

    if not isinstance(sentence, str):
        raise ValueError("state['user_input'] must be a string")
    if model is None or crf is None or tokenizer is None or device is None:
        raise ValueError("state must include bert_model, crf, tokenizer, device")

    label_to_slot = {
        "O": "O",
        "B-JOB": "직무",
        "I-JOB": "직무",
        "B-CAR": "경력",
        "I-CAR": "경력",
        "B-EDU": "학력",
        "I-EDU": "학력",
        "B-LOC": "지역",
        "I-LOC": "지역",
    }

    tokenized_input = tokenizer(sentence, return_tensors="pt", truncation=True)
    input_data = {k: v.to(device) for k, v in tokenized_input.items()}

    with torch.no_grad():
        logits = model(**input_data).logits
        predictions = crf.decode(logits)[0]
        predicted_token_class = [model.config.id2label[t] for t in predictions]

    decode = tokenizer.convert_ids_to_tokens(tokenized_input["input_ids"][0])

    entity: NormalizeEntityInputState = {
        "직무": "",
        "경력": "",
        "학력": "",
        "지역": "",
    }

    for word, pred in zip(decode, predicted_token_class):
        cleaned_word = word.replace("#", "")
        slot = label_to_slot.get(pred)
        if slot and slot != "O":
            current = entity.get(slot) or ""
            entity[slot] = current + cleaned_word

    return {
        "entities": entity,
        "지역": entity.get("지역"),
        "직무": entity.get("직무"),
        "경력": entity.get("경력"),
        "학력": entity.get("학력"),
    }


def normalize_and_validate_entities(
    state: GraphState,
) -> NormalizeAndValidateEntitiesResultState:
    typed_state: NormalizeAndValidateEntitiesState = {
        "entities": state.get("entities"),
        "지역": state.get("지역"),
        "직무": state.get("직무"),
        "경력": state.get("경력"),
        "학력": state.get("학력"),
    }

    entities = typed_state.get("entities")
    if isinstance(entities, dict):
        entity_dict: NormalizeEntityInputState = {
            "지역": entities.get("지역"),
            "직무": entities.get("직무"),
            "경력": entities.get("경력"),
            "학력": entities.get("학력"),
        }
    else:
        entity_dict = {
            "지역": typed_state.get("지역"),
            "직무": typed_state.get("직무"),
            "경력": typed_state.get("경력"),
            "학력": typed_state.get("학력"),
        }

    base_dir = os.getenv("JOB_SEARCH_ROOT")
    if not base_dir:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    synonym_dict_path = os.path.join(base_dir, "data", "url_exchanger", "synonym_dict.json")

    normalized_entities = normalize_entities(entity_dict, synonym_dict_path)
    missing_fields = check_missing_entities(normalized_entities)

    if missing_fields:
        message = generate_missing_message(missing_fields)
        return {
            "status": "incomplete",
            "message": message,
            "missing_fields": missing_fields,
            "normalized_entities": normalized_entities,
        }

    return {
        "status": "complete",
        "message": "모든 정보가 확인되었습니다.",
        "missing_fields": None,
        "normalized_entities": normalized_entities,
    }


def crawl_job_html_from_saramin(state: GraphState) -> CrawlingState:
    url = state.get("url")
    max_jobs = state.get("max_jobs", 50)

    if not isinstance(url, str) or not url.strip():
        raise ValueError("state['url'] must be a non-empty string")
    if max_jobs is not None and not isinstance(max_jobs, int):
        raise ValueError("state['max_jobs'] must be an int or None")

    html_contents = _crawl_job_html_from_saramin_tool(url, max_jobs)
    return {
        "html_contents": html_contents,
        "crawled_count": len(html_contents),
    }


def similarity_docs_retrieval(state: GraphState) -> RetrievalState:
    query = state.get("query")
    raw_documents = state.get("job_info_list")
    retriever = state.get("retriever")

    if not isinstance(query, str) or not query.strip():
        raise ValueError("state['query'] must be a non-empty string")
    if not isinstance(raw_documents, list):
        raise ValueError("state['job_info_list'] must be a list")

    documents = dict_to_str(raw_documents)
    if not documents:
        return {
            "retriever": retriever,
            "retrieved_job_info_list": [],
            "retrieved_scores": [],
        }

    needs_rebuild = True
    if isinstance(retriever, dict):
        cached_documents = retriever.get("documents")
        if retriever.get("is_indexed", False) and isinstance(cached_documents, list):
            needs_rebuild = cached_documents != documents

    if needs_rebuild:
        retriever = _build_hybrid_retriever_tool(documents)

    top_k = len(documents)
    retrieved_docs, retrieved_scores = _search_hybrid_retriever_tool(
        context=retriever,
        query=query,
        top_k=top_k,
        combination_method="weighted_average",
        use_query_expansion=True,
    )

    return {
        "retriever": retriever,
        "retrieved_job_info_list": retrieved_docs,
        "retrieved_scores": retrieved_scores,
    }


def generate_user_response_node(state: GraphState) -> dict[str, str]:
    query = state.get("query")
    retrieved_docs = state.get("retrieved_job_info_list")
    fallback_docs = state.get("job_info_list")

    if not isinstance(query, str) or not query.strip():
        raise ValueError("state['query'] must be a non-empty string")

    documents = None
    if isinstance(retrieved_docs, list) and retrieved_docs:
        documents = retrieved_docs
    elif isinstance(fallback_docs, list) and fallback_docs:
        documents = fallback_docs
    else:
        raise ValueError(
            "state must include a non-empty 'retrieved_job_info_list' or 'job_info_list'"
        )

    response = generate_response(query, documents)
    return {"user_response": response}


__all__ = [
    "singleton_model_node",
    "predict_crf_bert",
    "normalize_and_validate_entities",
    "crawl_job_html_from_saramin",
    "similarity_docs_retrieval",
    "generate_user_response_node",
]
