from src.retrieval import BM25Retriever, HybridRetriever, QueryProcessor


def build_hybrid_retriever(
    documents: list[str],
    bm25_weight: float = 0.6,
    embedding_weight: float = 0.4,
) -> HybridRetriever:
    retriever = HybridRetriever(bm25_weight=bm25_weight, embedding_weight=embedding_weight)
    retriever.build_index(documents)
    return retriever


__all__ = [
    "QueryProcessor",
    "BM25Retriever",
    "HybridRetriever",
    "build_hybrid_retriever",
]
