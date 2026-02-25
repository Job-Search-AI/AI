
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
    from .url_exchanger.bert_crf import predict_crf_bert as _fn

    return _fn(*args, **kwargs)


def normalize_and_validate_entities(*args, **kwargs):
    from .url_exchanger.entity_normalizer import normalize_and_validate_entities as _fn

    return _fn(*args, **kwargs)


def keep_loading_job_model(*args, **kwargs):
    from .utils.model_keeper import keep_loading_job_model as _fn

    return _fn(*args, **kwargs)


def mapping_url_query(*args, **kwargs):
    from .url_exchanger.url_mapper import mapping_url_query as _fn

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
