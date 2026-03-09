import threading
import os
from typing import Any, Callable

from dotenv import load_dotenv

# 모델 캐시는 state의 단일 소스를 재사용해 중복 캐시 객체 생성을 막는다.
from src.state.slices.singleton_model import get_model_cache

DEFAULT_BERT_MODEL_NAME = "klue/bert-base"
NER_LABELS = ["O", "B-JOB", "I-JOB", "B-CAR", "I-CAR", "B-EDU", "I-EDU", "B-LOC", "I-LOC"]

_CACHE_LOCK = threading.Lock()


def get_device() -> str:
    cache = get_model_cache()
    if cache["device"] is None:
        with _CACHE_LOCK:
            if cache["device"] is None:
                try:
                    from src.tools.utils.device_selector import get_device as _get_device

                    cache["device"] = _get_device()
                except Exception as exc:
                    raise RuntimeError(f"Failed to load device: {exc}") from exc

    return str(cache["device"])


def _ensure_ner_loaded(bert_model_name: str = DEFAULT_BERT_MODEL_NAME) -> None:
    cache = get_model_cache()
    if (
        cache["bert_model"] is not None
        and cache["tokenizer"] is not None
        and cache["crf"] is not None
    ):
        return

    device = get_device()

    with _CACHE_LOCK:
        if (
            cache["bert_model"] is not None
            and cache["tokenizer"] is not None
            and cache["crf"] is not None
        ):
            return

        try:
            from src.tools.slices.bert_crf import build_tag_map, get_bert_model_tokenizer
            from torchcrf import CRF

            label2id, id2label = build_tag_map(NER_LABELS)
            bert_model, tokenizer = get_bert_model_tokenizer(
                device=device,
                model_name=bert_model_name,
                label2id=label2id,
                id2label=id2label,
            )
            crf = CRF(len(label2id), batch_first=True).to(device)
        except Exception as exc:
            raise RuntimeError(f"Failed to load NER models: {exc}") from exc

        cache["device"] = device
        cache["bert_model"] = bert_model
        cache["tokenizer"] = tokenizer
        cache["crf"] = crf


def get_bert_model(bert_model_name: str = DEFAULT_BERT_MODEL_NAME) -> Any:
    _ensure_ner_loaded(bert_model_name)
    return get_model_cache()["bert_model"]


def get_tokenizer(bert_model_name: str = DEFAULT_BERT_MODEL_NAME) -> Any:
    _ensure_ner_loaded(bert_model_name)
    return get_model_cache()["tokenizer"]


def get_crf(bert_model_name: str = DEFAULT_BERT_MODEL_NAME) -> Any:
    _ensure_ner_loaded(bert_model_name)
    return get_model_cache()["crf"]


def get_embedding_model() -> Any:
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    load_dotenv(os.path.join(root_path, ".env"))
    use_openai = os.getenv("USE_OPENAI_MODELS", "false").lower() == "true"
    cache = get_model_cache()
    embedding_model = cache["embedding_model"]
    need_load = embedding_model is None
    if not need_load:
        has_openai = hasattr(embedding_model, "embed_query") and hasattr(embedding_model, "embed_documents")
        if use_openai and not has_openai:
            need_load = True
        if (not use_openai) and has_openai:
            need_load = True

    if need_load:
        with _CACHE_LOCK:
            embedding_model = cache["embedding_model"]
            need_load = embedding_model is None
            if not need_load:
                has_openai = hasattr(embedding_model, "embed_query") and hasattr(embedding_model, "embed_documents")
                if use_openai and not has_openai:
                    need_load = True
                if (not use_openai) and has_openai:
                    need_load = True
            if need_load:
                try:
                    from src.tools.embedding.model import get_model

                    cache["embedding_model"] = get_model(use_openai=use_openai)
                except Exception as exc:
                    raise RuntimeError(f"Failed to load embedding model: {exc}") from exc

    return cache["embedding_model"]


def get_llm() -> Callable[..., Any]:
    cache = get_model_cache()
    if cache["llm"] is None:
        with _CACHE_LOCK:
            if cache["llm"] is None:
                try:
                    from src.tools.llm.generator import generate_response

                    cache["llm"] = generate_response
                except Exception as exc:
                    raise RuntimeError(f"Failed to load llm function: {exc}") from exc

    llm = cache["llm"]
    if llm is None:
        raise RuntimeError("Failed to load llm function: value is None")
    return llm


def ensure_model_cache(bert_model_name: str = DEFAULT_BERT_MODEL_NAME) -> dict:
    root_path = os.getenv("JOB_SEARCH_ROOT")
    if not root_path:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    load_dotenv(os.path.join(root_path, ".env"))

    use_openai = os.getenv("USE_OPENAI_MODELS", "false").lower() == "true"
    get_device()
    if not use_openai:
        get_bert_model(bert_model_name)
        get_tokenizer(bert_model_name)
        get_crf(bert_model_name)
    get_embedding_model()
    get_llm()
    return get_model_cache()


__all__ = [
    "DEFAULT_BERT_MODEL_NAME",
    "NER_LABELS",
    "get_device",
    "get_bert_model",
    "get_tokenizer",
    "get_crf",
    "get_embedding_model",
    "get_llm",
    "ensure_model_cache",
]
