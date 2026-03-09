
def crawl_job_html_from_saramin(*args, **kwargs):
    # src 표면을 최소화하기 위해 공개 API도 tools 레이어로 직접 연결한다.
    from src.tools.slices.crawling import crawl_job_html_from_saramin as _fn

    return _fn(*args, **kwargs)


def similarity_docs_retrieval(*args, **kwargs):
    from src.tools.embedding.model import similarity_docs_retrieval as _fn

    return _fn(*args, **kwargs)


def generate_response(*args, **kwargs):
    from src.tools.llm.generator import generate_response as _fn

    return _fn(*args, **kwargs)


def parsing_job_info(*args, **kwargs):
    from src.tools.parsing.main import parsing_job_info as _fn

    return _fn(*args, **kwargs)


def predict_crf_bert(*args, **kwargs):
    # 레거시 모듈을 legacy 패키지로 옮겼지만 공개 API는 유지해야 하므로 lazy import만 경로를 바꾼다.
    from legacy.src.bert_crf.bert_crf import predict_crf_bert as _fn

    return _fn(*args, **kwargs)


def normalize_and_validate_entities(*args, **kwargs):
    # 외부 호출부가 from src import ... 를 계속 쓸 수 있게 레거시 경로를 여기에서 흡수한다.
    from legacy.src.entity_normalizer.entity_normalizer import normalize_and_validate_entities as _fn

    return _fn(*args, **kwargs)


def keep_loading_job_model(*args, **kwargs):
    # 모델 캐시 로더도 legacy로 이동했기 때문에 기존 함수명에 새 위치를 연결한다.
    from legacy.src.utils.model_keeper import keep_loading_job_model as _fn

    return _fn(*args, **kwargs)


def mapping_url_query(*args, **kwargs):
    # URL 매퍼는 레거시로 분리됐지만 이 함수는 호환 레이어 역할만 담당한다.
    from legacy.src.url_mapper.url_mapper import mapping_url_query as _fn

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
