from typing import Any

# 검색 구현도 tools 내부 패키지로 이동해 src 비핵심 경로 의존을 제거한다.
from src.tools.retrieval import BM25Retriever, QueryProcessor
from src.tools.retrieval.hybrid_retriever import (
    build_hybrid_retriever as _build_hybrid_retriever,
    get_hybrid_component_results,
    get_hybrid_statistics,
    search_hybrid_retriever as _search_hybrid_retriever_core,
    set_hybrid_weights as _set_hybrid_weights,
)
from src.tools.utils.str_generator import dict_to_str


def _validate_search_inputs(
    query: str,
    documents: list[object],
    top_k: int | None,
    combination_method: str,
) -> None:
    # 노드 입력은 외부 I/O 경계이므로 검색 전에 필수 타입/값을 먼저 검증한다.
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(documents, list):
        raise ValueError("documents must be a list")

    # top_k는 None(자동 결정) 또는 양의 정수만 허용해 하위 검색기의 계약을 지킨다.
    if top_k is not None and (not isinstance(top_k, int) or top_k <= 0):
        raise ValueError("top_k must be a positive integer or None")

    # 결합 방식은 기존 하이브리드 검색기에서 지원하는 두 모드만 허용한다.
    if combination_method not in {"weighted_average", "rrf"}:
        raise ValueError(f"unsupported combination_method: {combination_method}")


def _normalize_documents_for_retrieval(documents: list[object]) -> list[str]:
    # dict/list 혼합 입력을 문자열 리스트로 통일해 인덱스 구축 입력을 고정한다.
    normalized_documents = dict_to_str(documents)
    if not isinstance(normalized_documents, list):
        raise ValueError("documents must be convertible to a list of strings")

    # 검색 인덱스는 문자열 문서 목록을 전제로 하므로 원소 타입도 함께 검증한다.
    if any(not isinstance(document, str) for document in normalized_documents):
        raise ValueError("documents must contain only strings after normalization")
    return normalized_documents


def _needs_rebuild_retriever(
    retriever: object | None,
    documents: list[str],
    use_openai: bool,
) -> bool:
    # 재사용 가능 여부는 기존 컨텍스트 타입/인덱싱 상태/문서 일치 여부로 판단한다.
    target_provider = "openai" if use_openai else "local"
    if not isinstance(retriever, dict):
        return True
    if not retriever.get("is_indexed", False):
        return True
    if retriever.get("embedding_provider") != target_provider:
        return True
    cached_documents = retriever.get("documents")
    if not isinstance(cached_documents, list):
        return True
    return cached_documents != documents


def _resolve_top_k(top_k: int | None, documents: list[str]) -> int:
    # 기본값(None)일 때는 현재 문서 수만큼 검색하고, 지정값은 문서 수로 상한을 둔다.
    if top_k is None:
        return len(documents)
    return min(top_k, len(documents))


def build_hybrid_retriever(
    documents: list[str],
    bm25_weight: float = 0.5,
    embedding_weight: float = 0.5,
    use_openai: bool = False,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, Any]:
    # 원본 검색 구현은 유지하고 tools 레이어는 호출 경로만 통일한다.
    return _build_hybrid_retriever(
        documents=documents,
        bm25_weight=bm25_weight,
        embedding_weight=embedding_weight,
        use_openai=use_openai,
        k1=k1,
        b=b,
    )


def set_hybrid_weights(
    context: dict[str, Any],
    bm25_weight: float,
    embedding_weight: float,
) -> dict[str, Any]:
    # 가중치 갱신도 원본 구현을 그대로 위임해 계산 규칙을 바꾸지 않는다.
    return _set_hybrid_weights(
        context=context,
        bm25_weight=bm25_weight,
        embedding_weight=embedding_weight,
    )


def search_hybrid_retriever(
    query: str,
    documents: list[object],
    retriever: object | None = None,
    top_k: int | None = None,
    combination_method: str = "weighted_average",
    use_query_expansion: bool = True,
    bm25_weight: float = 0.5,
    embedding_weight: float = 0.5,
    use_openai: bool = False,
) -> dict[str, object]:
    # 최상위 검색 함수 하나에서 선행 단계와 본 검색을 모두 처리하도록 묶는다.
    _validate_search_inputs(
        query=query,
        documents=documents,
        top_k=top_k,
        combination_method=combination_method,
    )

    # 검색기는 문자열 문서 리스트를 기준으로 인덱스를 유지하므로 먼저 정규화한다.
    normalized_documents = _normalize_documents_for_retrieval(documents)
    if not normalized_documents:
        return {
            "retriever": retriever,
            "retrieved_job_info_list": [],
            "retrieved_scores": [],
        }

    # 기존 인덱스 재사용 가능 시 그대로 쓰고, 문서가 바뀐 경우에만 재빌드한다.
    if _needs_rebuild_retriever(retriever, normalized_documents, use_openai):
        retriever = build_hybrid_retriever(
            documents=normalized_documents,
            bm25_weight=bm25_weight,
            embedding_weight=embedding_weight,
            use_openai=use_openai,
        )
    else:
        retriever = set_hybrid_weights(
            context=retriever,
            bm25_weight=bm25_weight,
            embedding_weight=embedding_weight,
        )

    # top_k를 최종 확정한 뒤 원본 검색기를 호출해 결과를 partial-state 형태로 반환한다.
    resolved_top_k = _resolve_top_k(top_k, normalized_documents)
    retrieved_docs, retrieved_scores = _search_hybrid_retriever_core(
        context=retriever,
        query=query,
        top_k=resolved_top_k,
        combination_method=combination_method,
        use_query_expansion=use_query_expansion,
    )
    return {
        "retriever": retriever,
        "retrieved_job_info_list": retrieved_docs,
        "retrieved_scores": retrieved_scores,
    }


__all__ = [
    "QueryProcessor",
    "BM25Retriever",
    "build_hybrid_retriever",
    "search_hybrid_retriever",
    "set_hybrid_weights",
    "get_hybrid_component_results",
    "get_hybrid_statistics",
]
