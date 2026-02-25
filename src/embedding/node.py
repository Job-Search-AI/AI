from src.state import GraphState, RetrievalState
from src.utils import dict_to_str


def similarity_docs_retrieval(state: GraphState) -> RetrievalState:
    query = state.get("query")
    documents = state.get("job_info_list")
    embedding_model = state.get("embedding_model")
    precomputed_doc_embeddings = state.get("precomputed_doc_embeddings")

    if not isinstance(query, str) or not query.strip():
        raise ValueError("state['query'] must be a non-empty string")
    if not isinstance(documents, list):
        raise ValueError("state['job_info_list'] must be a list")
    if embedding_model is None:
        raise ValueError("state must include 'embedding_model'")

    documents_for_embedding = dict_to_str(documents)
    if not documents_for_embedding:
        return {
            "retrieved_job_info_list": [],
            "retrieved_scores": [],
        }

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

    return {
        "retrieved_job_info_list": retrieved_docs,
        "retrieved_scores": retrieved_scores,
    }
