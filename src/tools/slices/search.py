__all__ = ["IndexConfig", "FAISSIndexManager", "FAISSBenchmark"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    # 검색 인덱스 구현도 tools 내부 패키지에서 로드한다.
    from src.tools.search.faiss_manager import FAISSBenchmark, FAISSIndexManager, IndexConfig

    mapping = {
        "IndexConfig": IndexConfig,
        "FAISSIndexManager": FAISSIndexManager,
        "FAISSBenchmark": FAISSBenchmark,
    }
    return mapping[name]
