from typing import Any

# 문자열 변환 유틸도 tools 내부로 통일해 코어 외부 의존을 없앤다.
from src.tools.utils.str_generator import dict_to_str


def similarity_docs_retrieval(
    query: str,
    documents: list[Any],
    embedding_model: Any,
    precomputed_doc_embeddings: Any = None,
) -> tuple[list[str], list[float]]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(documents, list):
        raise ValueError("documents must be a list")
    if embedding_model is None:
        raise ValueError("embedding_model is required")

    documents_for_embedding = dict_to_str(documents)
    if not documents_for_embedding:
        return [], []

    query_embeddings = embedding_model.encode(query, prompt_name="query")
    if precomputed_doc_embeddings is not None:
        document_embeddings = precomputed_doc_embeddings
    else:
        document_embeddings = embedding_model.encode(documents_for_embedding, batch_size=2)

    scores = embedding_model.similarity(query_embeddings, document_embeddings)
    doc_score_pairs = sorted(
        zip(documents_for_embedding, scores[0]),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    retrieved_docs: list[str] = []
    retrieved_scores: list[float] = []
    for document, score in doc_score_pairs:
        retrieved_docs.append(document)
        retrieved_scores.append(float(score))

    return retrieved_docs, retrieved_scores
