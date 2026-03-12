"""
하이브리드 검색 시스템 (BM25 + 임베딩 검색) - 함수형 API
"""

from typing import Any

import numpy as np

from .bm25_retriever import BM25Retriever
from .query_processor import QueryProcessor


def _ensure_indexed(context: dict[str, Any]) -> None:
    if not isinstance(context, dict) or not context.get("is_indexed", False):
        raise ValueError("인덱스가 구축되지 않았습니다. build_hybrid_retriever()를 먼저 호출하세요.")


def _normalize_scores(scores: list[float]) -> np.ndarray:
    if not scores:
        return np.array([])

    scores_array = np.array(scores, dtype=np.float32)
    max_score = float(np.max(scores_array))
    min_score = float(np.min(scores_array))
    if max_score == min_score:
        return np.ones(len(scores))
    return (scores_array - min_score) / (max_score - min_score)


def _combine_scores_weighted_average(
    bm25_scores: np.ndarray,
    embedding_scores: np.ndarray,
    bm25_weight: float,
    embedding_weight: float,
) -> np.ndarray:
    return (bm25_weight * bm25_scores) + (embedding_weight * embedding_scores)


def _combine_scores_rrf(
    bm25_results: list[tuple[int, float]],
    embedding_results: list[tuple[int, float]],
    k: int = 60,
) -> list[tuple[int, float]]:
    rrf_scores: dict[int, float] = {}

    for rank, (doc_idx, _score) in enumerate(bm25_results):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1 / (k + rank + 1))

    for rank, (doc_idx, _score) in enumerate(embedding_results):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1 / (k + rank + 1))

    return sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)


def _combine_weighted_average(
    context: dict[str, Any],
    bm25_docs: list[str],
    bm25_scores: list[float],
    embedding_docs: list[str],
    embedding_scores: list[float],
    top_k: int,
) -> tuple[list[str], list[float]]:
    documents = context["documents"]
    doc_to_idx = {doc: idx for idx, doc in enumerate(documents)}

    bm25_results: dict[int, float] = {}
    for doc, score in zip(bm25_docs, bm25_scores):
        if doc in doc_to_idx:
            bm25_results[doc_to_idx[doc]] = score

    embedding_results: dict[int, float] = {}
    for doc, score in zip(embedding_docs, embedding_scores):
        if doc in doc_to_idx:
            embedding_results[doc_to_idx[doc]] = score

    all_doc_indices = set(bm25_results.keys()) | set(embedding_results.keys())
    if not all_doc_indices:
        return [], []

    all_bm25_scores = [bm25_results.get(idx, 0.0) for idx in all_doc_indices]
    all_embedding_scores = [embedding_results.get(idx, 0.0) for idx in all_doc_indices]

    normalized_bm25 = _normalize_scores(all_bm25_scores)
    normalized_embedding = _normalize_scores(all_embedding_scores)
    combined_scores = _combine_scores_weighted_average(
        normalized_bm25,
        normalized_embedding,
        context["bm25_weight"],
        context["embedding_weight"],
    )

    doc_score_pairs = list(zip(all_doc_indices, combined_scores))
    doc_score_pairs.sort(key=lambda item: item[1], reverse=True)
    top_results = doc_score_pairs[:top_k]

    final_docs = [documents[doc_idx] for doc_idx, _score in top_results]
    final_scores = [float(score) for _doc_idx, score in top_results]
    return final_docs, final_scores


def _combine_rrf(
    context: dict[str, Any],
    bm25_docs: list[str],
    bm25_scores: list[float],
    embedding_docs: list[str],
    embedding_scores: list[float],
    top_k: int,
) -> tuple[list[str], list[float]]:
    documents = context["documents"]
    doc_to_idx = {doc: idx for idx, doc in enumerate(documents)}

    bm25_ranked = [
        (doc_to_idx[doc], score)
        for doc, score in zip(bm25_docs, bm25_scores)
        if doc in doc_to_idx
    ]
    embedding_ranked = [
        (doc_to_idx[doc], score)
        for doc, score in zip(embedding_docs, embedding_scores)
        if doc in doc_to_idx
    ]

    rrf_results = _combine_scores_rrf(bm25_ranked, embedding_ranked)
    top_results = rrf_results[:top_k]

    final_docs = [documents[doc_idx] for doc_idx, _score in top_results]
    final_scores = [float(score) for _doc_idx, score in top_results]
    return final_docs, final_scores


def build_hybrid_retriever(
    documents: list[str],
    bm25_weight: float = 0.5,
    embedding_weight: float = 0.5,
    use_openai: bool = False,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, Any]:
    print("하이브리드 검색 인덱스 구축 시작...")
    from src.tools.embedding.model import get_model

    bm25_retriever = BM25Retriever(k1=k1, b=b)
    query_processor = QueryProcessor()

    print("1. BM25 인덱스 구축...")
    bm25_retriever.build_index(documents)

    print("2. 임베딩 모델 로드 및 문서 임베딩 계산...")
    embedding_model = get_model(use_openai=use_openai)
    if use_openai:
        document_embeddings = embedding_model.embed_documents(documents)
        embedding_provider = "openai"
    else:
        document_embeddings = embedding_model.encode(documents, batch_size=2)
        embedding_provider = "local"

    print("하이브리드 검색 인덱스 구축 완료")
    return {
        "bm25_weight": bm25_weight,
        "embedding_weight": embedding_weight,
        "bm25_retriever": bm25_retriever,
        "query_processor": query_processor,
        "embedding_model": embedding_model,
        "document_embeddings": document_embeddings,
        "is_indexed": True,
        "documents": list(documents),
        "embedding_provider": embedding_provider,
    }


def search_hybrid_retriever(
    context: dict[str, Any],
    query: str,
    top_k: int = 10,
    combination_method: str = "weighted_average",
    use_query_expansion: bool = True,
) -> tuple[list[str], list[float]]:
    _ensure_indexed(context)  # 인덱스가 준비되었는지 검사
    if not query.strip(): return [], []
    from src.tools.embedding.model import similarity_docs_retrieval

    # 쿼리 확장 적용 여부에 따라 검색어 결정
    if use_query_expansion:
        expanded_query = context["query_processor"].get_expanded_query_string(query)
        search_query = expanded_query if expanded_query.strip() else query
    else:
        search_query = query

    # BM25 검색 실행 (top_k * 2 개까지)
    bm25_docs, bm25_scores = context["bm25_retriever"].search(search_query, top_k=top_k * 2)

    # 임베딩 기반 유사도 검색 실행
    embedding_docs, embedding_scores = similarity_docs_retrieval(
        search_query,
        context["documents"],
        embedding_model=context["embedding_model"],
        precomputed_doc_embeddings=context["document_embeddings"],
    )
    embedding_docs = embedding_docs[: top_k * 2]
    embedding_scores = embedding_scores[: top_k * 2]

    # 결합 방식에 따라 최종 결과 생성
    if combination_method == "weighted_average":
        return _combine_weighted_average(context, bm25_docs, bm25_scores, embedding_docs, embedding_scores, top_k)
    elif combination_method == "rrf":
        return _combine_rrf(context, bm25_docs, bm25_scores, embedding_docs, embedding_scores, top_k)
    else:
        raise ValueError(f"지원하지 않는 결합 방법: {combination_method}")


def set_hybrid_weights(
    context: dict[str, Any],
    bm25_weight: float,
    embedding_weight: float,
) -> dict[str, Any]:
    _ensure_indexed(context)

    total_weight = bm25_weight + embedding_weight
    if total_weight == 0:
        raise ValueError("가중치의 합이 0이 될 수 없습니다.")

    context["bm25_weight"] = bm25_weight / total_weight
    context["embedding_weight"] = embedding_weight / total_weight
    print(
        f"가중치 업데이트: BM25={context['bm25_weight']:.2f}, "
        f"Embedding={context['embedding_weight']:.2f}"
    )
    return context


def get_hybrid_component_results(
    context: dict[str, Any],
    query: str,
    top_k: int = 10,
) -> dict[str, Any]:
    _ensure_indexed(context)
    from src.tools.embedding.model import similarity_docs_retrieval

    expanded_query = context["query_processor"].get_expanded_query_string(query)

    bm25_docs, bm25_scores = context["bm25_retriever"].search(expanded_query, top_k)
    embedding_docs, embedding_scores = similarity_docs_retrieval(
        expanded_query,
        context["documents"],
        embedding_model=context["embedding_model"],
        precomputed_doc_embeddings=context["document_embeddings"],
    )
    embedding_docs = embedding_docs[:top_k]
    embedding_scores = embedding_scores[:top_k]

    return {
        "original_query": query,
        "expanded_query": expanded_query,
        "bm25_results": {
            "documents": bm25_docs,
            "scores": bm25_scores,
        },
        "embedding_results": {
            "documents": embedding_docs,
            "scores": embedding_scores,
        },
    }


def get_hybrid_statistics(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}

    is_indexed = bool(context.get("is_indexed", False))
    documents = context.get("documents", [])

    stats: dict[str, Any] = {
        "is_indexed": is_indexed,
        "num_documents": len(documents) if isinstance(documents, list) else 0,
        "weights": {
            "bm25": context.get("bm25_weight"),
            "embedding": context.get("embedding_weight"),
        },
    }

    if is_indexed:
        stats["bm25_stats"] = context["bm25_retriever"].get_index_statistics()
        stats["embedding_model"] = (
            type(context["embedding_model"]).__name__ if context.get("embedding_model") else None
        )
    return stats


__all__ = [
    "build_hybrid_retriever",
    "search_hybrid_retriever",
    "set_hybrid_weights",
    "get_hybrid_component_results",
    "get_hybrid_statistics",
]
