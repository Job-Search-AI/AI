import json
import os
import resource
import sys
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.state import (
    CrawlingState,
    GraphState,
    NormalizeAndValidateEntitiesResultState,
    NormalizeAndValidateEntitiesState,
    NormalizeEntityInputState,
    ParsingState,
    PredictCrfBertResultState,
    RetrievalState,
    SingletonModelNodeUpdate,
)
from src.tools.slices.crawling import crawl_job_html_from_saramin as _crawl_job_html_from_saramin_tool
from src.tools.slices.parsing import parsing_job_info as _parsing_job_info_tool
from src.tools.slices.retrieval import search_hybrid_retriever as _search_hybrid_retriever_tool
from src.tools.slices.llm import generate_response
from src.tools.slices.singleton_model import (
    DEFAULT_BERT_MODEL_NAME,
    ensure_model_cache,
    get_model_cache,
)
from src.tools.slices.entity_normalizer import (
    check_missing_entities,
    generate_missing_message,
    normalize_entities,
)


def _log_mem(state: GraphState, stage: str, crawled_count: int) -> None:
    if os.getenv("MEM_LOG_ENABLED", "false").lower() != "true":
        return

    started_ms = state.get("_started_ms")
    elapsed_ms = 0
    if isinstance(started_ms, int):
        elapsed_ms = int(time.time() * 1000) - started_ms

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        rss_mb = round(rss / 1024 / 1024, 2)
    else:
        rss_mb = round(rss / 1024, 2)

    payload = {
        "request_id": state.get("_request_id", ""),
        "stage": stage,
        "rss_mb": rss_mb,
        "crawled_count": crawled_count,
        "elapsed_ms": elapsed_ms,
    }
    print(json.dumps(payload, ensure_ascii=False))


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


def predict_ner(user_input: str) -> dict[str, str]:
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(root_path, ".env"))

    if not isinstance(user_input, str):
        raise ValueError("user_input must be a string")

    entity = {
        "지역": "",
        "직무": "",
        "경력": "",
        "학력": "",
    }
    use_openai = os.getenv("USE_OPENAI_MODELS", "false").lower() == "true"

    if use_openai:
        timeout = os.getenv("OPENAI_TIMEOUT_SECONDS")
        retries = os.getenv("OPENAI_MAX_RETRIES")
        llm = ChatOpenAI(
            model=os.getenv("NER_MODEL_NAME", "gpt-5-nano"),
            timeout=float(timeout) if timeout else None,
            max_retries=int(retries) if retries else None,
        )
        schema = {
            "title": "ner",
            "type": "object",
            "properties": {
                "지역": {
                    "type": "string",
                    "description": "사용자 문장에 있는 지역. 없으면 빈 문자열.",
                },
                "직무": {
                    "type": "string",
                    "description": "사용자 문장에 있는 직무. 없으면 빈 문자열.",
                },
                "경력": {
                    "type": "string",
                    "description": "사용자 문장에 있는 경력. 없으면 빈 문자열.",
                },
                "학력": {
                    "type": "string",
                    "description": "사용자 문장에 있는 학력. 없으면 빈 문자열.",
                },
            },
            "required": ["지역", "직무", "경력", "학력"],
            "additionalProperties": False,
        }
        prompt = "\n".join(
            [
                "사용자 문장에서 지역, 직무, 경력, 학력만 추출한다.",
                "문장에 없는 값은 반드시 빈 문자열로 반환한다.",
                "추론으로 값을 채우지 않는다.",
                user_input,
            ]
        )
        result = llm.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
        ).invoke(prompt)

        for key in entity:
            value = result.get(key, "")
            if isinstance(value, str):
                entity[key] = value.strip()
        return entity
    import torch

    cache = get_model_cache()
    model = cache.get("bert_model")
    crf = cache.get("crf")
    tokenizer = cache.get("tokenizer")
    device = cache.get("device")

    if model is None or crf is None or tokenizer is None or device is None:
        ensure_model_cache(DEFAULT_BERT_MODEL_NAME)
        cache = get_model_cache()
        model = cache.get("bert_model")
        crf = cache.get("crf")
        tokenizer = cache.get("tokenizer")
        device = cache.get("device")

    if model is None or crf is None or tokenizer is None or device is None:
        raise ValueError("NER model cache is empty")

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
    tokenized_input = tokenizer(user_input, return_tensors="pt", truncation=True)
    input_data = {}
    for key, value in tokenized_input.items():
        input_data[key] = value.to(device)

    with torch.no_grad():
        logits = model(**input_data).logits
        predictions = crf.decode(logits)[0]
        predicted_token_class = []
        for token_id in predictions:
            predicted_token_class.append(model.config.id2label[token_id])

    decode = tokenizer.convert_ids_to_tokens(tokenized_input["input_ids"][0])

    for word, pred in zip(decode, predicted_token_class):
        cleaned_word = word.replace("#", "")
        slot = label_to_slot.get(pred)
        if slot and slot != "O":
            current = entity.get(slot) or ""
            entity[slot] = current + cleaned_word

    return entity


def predict_crf_bert(state: GraphState) -> PredictCrfBertResultState:
    sentence = state.get("user_input")

    if not isinstance(sentence, str):
        raise ValueError("state['user_input'] must be a string")
    entity: NormalizeEntityInputState = predict_ner(sentence)
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
    # 실제 데이터 디렉토리명(url_exchager)에 맞춰 경로를 고정해 실행 시 파일 누락을 막는다.
    synonym_dict_path = os.path.join(base_dir, "data", "url_exchager", "synonym_dict.json")

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


def mapping_url_query_node(state: GraphState) -> dict[str, str]:
    # normalize 단계 결과를 그대로 이어받아 URL 생성만 담당한다.
    normalized_entities = state.get("normalized_entities")
    if not isinstance(normalized_entities, dict):
        raise ValueError("state['normalized_entities'] must be a dict")

    # URL 매핑은 4개 슬롯이 모두 채워져 있어야 하므로 None/누락 여부를 먼저 검증한다.
    required_fields = ("지역", "직무", "경력", "학력")
    invalid_fields = [
        field
        for field in required_fields
        if field not in normalized_entities or normalized_entities.get(field) is None
    ]
    if invalid_fields:
        raise ValueError(
            "state['normalized_entities'] must include non-null values for: "
            + ", ".join(invalid_fields)
        )

    # 기존 계약을 유지하기 위해 동일한 query_map 경로(data/url_exchager)를 사용한다.
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    query_map_path = os.path.join(root_path, "data", "url_exchager", "query_map.json")

    # query_map을 읽은 뒤 슬롯별 코드를 순서대로 이어 붙여 사람인 검색 URL을 만든다.
    with open(query_map_path, "r", encoding="utf-8") as f:
        query_map_data = json.load(f)

    url_base = "https://www.saramin.co.kr/zf_user/search?searchType=search?"
    for idx, (key, value) in enumerate(normalized_entities.items()):
        mapped = query_map_data[key][value]
        if idx == 0:
            url_base += mapped
        else:
            url_base += "&" + mapped

    # 기존 동작과 동일하게 학력/경력 무관 옵션을 마지막에 덧붙인다.
    url_base += "&edu_none=y&exp_none=y"
    return {"url": url_base}


def crawl_job_html_from_saramin(state: GraphState) -> CrawlingState:
    url = state.get("url")
    max_jobs = state.get("max_jobs")

    if not isinstance(url, str) or not url.strip():
        raise ValueError("state['url'] must be a non-empty string")
    if max_jobs is not None and not isinstance(max_jobs, int):
        raise ValueError("state['max_jobs'] must be an int or None")
    if max_jobs is None:
        max_jobs = int(os.getenv("MAX_JOBS_DEFAULT", "8"))

    max_jobs_limit = int(os.getenv("MAX_JOBS_LIMIT", "12"))
    if max_jobs > max_jobs_limit:
        max_jobs = max_jobs_limit

    html_contents = _crawl_job_html_from_saramin_tool(url, max_jobs)
    crawled_count = len(html_contents)
    _log_mem(state, "after_crawl", crawled_count)
    return {
        "max_jobs": max_jobs,
        "html_contents": html_contents,
        "crawled_count": crawled_count,
    }


def parse_job_info_node(state: GraphState) -> ParsingState:
    # 파싱 노드는 크롤링 단계 결과(html_contents)를 받아 문자열 리스트로 변환한다.
    html_contents = state.get("html_contents")
    if not isinstance(html_contents, list):
        raise ValueError("state['html_contents'] must be a list")

    # 파싱 로직은 tools 레이어를 단일 진입점으로 써서 재사용 경로를 통일한다.
    parsed_list = _parsing_job_info_tool(html_contents)
    crawled_count = state.get("crawled_count", len(html_contents))
    if not isinstance(crawled_count, int):
        crawled_count = len(html_contents)
    _log_mem(state, "after_parse", crawled_count)
    return {"job_info_list": parsed_list}


def search_hybrid_retriever_node(state: GraphState) -> RetrievalState:
    # 검색 노드는 쿼리/문서/옵션을 모아 tools의 최상위 검색 함수에 그대로 위임한다.
    query = state.get("query")
    raw_documents = state.get("job_info_list")
    retriever = state.get("retriever")
    top_k = state.get("retrieval_top_k")
    if isinstance(top_k, int) and top_k > 5:
        top_k = 5
    combination_method = state.get("retrieval_combination_method", "weighted_average")
    use_query_expansion = state.get("retrieval_use_query_expansion", True)
    bm25_weight = state.get("retrieval_bm25_weight", 0.5)
    embedding_weight = state.get("retrieval_embedding_weight", 0.5)
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(root_path, ".env"))
    use_openai = os.getenv("USE_OPENAI_MODELS", "false").lower() == "true"

    # state 검증은 tools에서 수행하므로 노드는 옵션 전달과 반환 포맷 유지에 집중한다.
    result = _search_hybrid_retriever_tool(
        query=query,
        documents=raw_documents,
        retriever=retriever,
        top_k=top_k,
        combination_method=combination_method,
        use_query_expansion=use_query_expansion,
        bm25_weight=bm25_weight,
        embedding_weight=embedding_weight,
        use_openai=use_openai,
    )
    crawled_count = state.get("crawled_count", 0)
    if not isinstance(crawled_count, int):
        crawled_count = 0
    _log_mem(state, "after_retrieval", crawled_count)
    return {
        "retriever": result["retriever"],
        "retrieved_job_info_list": result["retrieved_job_info_list"],
        "retrieved_scores": result["retrieved_scores"],
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
    "predict_ner",
    "predict_crf_bert",
    "normalize_and_validate_entities",
    "mapping_url_query_node",
    "crawl_job_html_from_saramin",
    "parse_job_info_node",
    "search_hybrid_retriever_node",
    "generate_user_response_node",
]
