
def crawl_job_html_from_saramin(*args, **kwargs):
    from .crawling.job_crawler import crawl_job_html_from_saramin as _fn

    return _fn(*args, **kwargs)


def similarity_docs_retrieval(*args, **kwargs):
    from .embedding.model import similarity_docs_retrieval as _fn

    return _fn(*args, **kwargs)


def generate_response(*args, **kwargs):
    from .llm.generator import generate_response as _fn

    return _fn(*args, **kwargs)


def parsing_job_info(*args, **kwargs):
    from .parsing.main import parsing_job_info as _fn

    return _fn(*args, **kwargs)


def predict_crf_bert(*args, **kwargs):
    # url_exchanger 경로를 제거하고 분리된 bert_crf 패키지로 직접 연결한다.
    from .bert_crf.bert_crf import predict_crf_bert as _fn

    return _fn(*args, **kwargs)


def normalize_and_validate_entities(*args, **kwargs):
    # 엔티티 정규화 모듈도 분리된 패키지 경로로 연결한다.
    from .entity_normalizer.entity_normalizer import normalize_and_validate_entities as _fn

    return _fn(*args, **kwargs)


def keep_loading_job_model(*args, **kwargs):
    from .utils.model_keeper import keep_loading_job_model as _fn

    return _fn(*args, **kwargs)


def mapping_url_query(*args, **kwargs):
    # URL 매퍼는 새 패키지에서 lazy import 하여 기존 공개 API를 유지한다.
    from .url_mapper.url_mapper import mapping_url_query as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "crawl_job_html_from_saramin",
    "similarity_docs_retrieval",
    "generate_response",
    "parsing_job_info",
    "predict_crf_bert",
    "normalize_and_validate_entities",
    "keep_loading_job_model",
    "mapping_url_query",
]
