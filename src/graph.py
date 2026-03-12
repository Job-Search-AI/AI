import json
import os
import resource
import sys
import time
import uuid
from collections.abc import Mapping
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.node import (
    crawl_job_html_from_saramin,
    generate_user_response_node,
    mapping_url_query_node,
    normalize_and_validate_entities,
    parse_job_info_node,
    predict_crf_bert,
    search_hybrid_retriever_node,
    singleton_model_node,
)
from src.router import ROUTE_MAP_URL, ROUTE_NEED_MORE_INFO, route_after_normalize_entities
from src.state import GraphState

_COMPILED_GRAPH: Any | None = None


def _get_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(rss / 1024 / 1024, 2)
    return round(rss / 1024, 2)


def _log_mem(state: Mapping[str, Any], stage: str) -> None:
    if os.getenv("MEM_LOG_ENABLED", "false").lower() != "true":
        return

    started_ms = state.get("_started_ms")
    elapsed_ms = 0
    if isinstance(started_ms, int):
        elapsed_ms = int(time.time() * 1000) - started_ms

    crawled_count = state.get("crawled_count", 0)
    if not isinstance(crawled_count, int):
        crawled_count = 0

    cgroup_mb = 0.0
    cgroup_path = "/sys/fs/cgroup/memory.current"
    if os.path.exists(cgroup_path):
        with open(cgroup_path, "r", encoding="utf-8") as f:
            cgroup_raw = f.read().strip()
        if cgroup_raw:
            cgroup_mb = round(int(cgroup_raw) / 1024 / 1024, 2)
    else:
        cgroup_path = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
        if os.path.exists(cgroup_path):
            with open(cgroup_path, "r", encoding="utf-8") as f:
                cgroup_raw = f.read().strip()
            if cgroup_raw:
                cgroup_mb = round(int(cgroup_raw) / 1024 / 1024, 2)

    payload = {
        "request_id": state.get("_request_id", ""),
        "stage": stage,
        "rss_mb": _get_rss_mb(),
        "cgroup_mb": cgroup_mb,
        "crawled_count": crawled_count,
        "elapsed_ms": elapsed_ms,
    }
    print(json.dumps(payload, ensure_ascii=False))


def build_graph() -> StateGraph:
    """
    노드를 연결하여 그래프를 빌드한다.
    get_compiled_graph()를 통해 간접 사용.
    """
    # 그래프는 노드 연결 규칙을 한 곳에 모아, 파이프라인 흐름을 코드로 명시한다.
    workflow = StateGraph(GraphState)

    # 주요 노드 추가
    workflow.add_node("singleton_model", singleton_model_node)
    workflow.add_node("predict_entities", predict_crf_bert)
    workflow.add_node("normalize_entities", normalize_and_validate_entities)
    workflow.add_node("map_url", mapping_url_query_node)
    workflow.add_node("crawl_html", crawl_job_html_from_saramin)
    workflow.add_node("parse_job_info", parse_job_info_node)
    workflow.add_node("search_hybrid", search_hybrid_retriever_node)
    workflow.add_node("generate_user_response", generate_user_response_node)

    # 초기시작: 모델 로드 -> 엔티티 추출 -> 정규화
    workflow.add_edge(START, "singleton_model")
    workflow.add_edge("singleton_model", "predict_entities")
    workflow.add_edge("predict_entities", "normalize_entities")

    # 조건분기: 정보 부족 시 종료, 충분하면 URL 매핑으로 진행
    workflow.add_conditional_edges(
        "normalize_entities",
        route_after_normalize_entities,
        {
            ROUTE_NEED_MORE_INFO: END,
            ROUTE_MAP_URL: "map_url",
        },
    )

    # 정보가 충분한 경우에만 URL 생성 이후 검색/응답 단계로 이어진다.
    workflow.add_edge("map_url", "crawl_html")
    workflow.add_edge("crawl_html", "parse_job_info")
    workflow.add_edge("parse_job_info", "search_hybrid")
    workflow.add_edge("search_hybrid", "generate_user_response")
    workflow.add_edge("generate_user_response", END)
    return workflow

def get_compiled_graph() -> Any:
    """
    컴파일된 그래프 인스턴스를 싱글턴처럼 관리하여 재사용한다.
    """
    global _COMPILED_GRAPH

    # 최초 호출 시에만 build_graph().compile() 실행
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph().compile()
    return _COMPILED_GRAPH

def run_job_search_graph(initial_state: Mapping[str, Any]) -> GraphState:
    """
    그래프를 실행한다.

    사용법
    result = graph_module.run_job_search_graph({"user_input": "서울 백엔드 신입"})
    """
    # 입력이 매핑 타입이 아니면 오류 발생
    if not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be a mapping")

    # 입력 원본을 직접 바꾸지 않기 위해 복사본을 만들어 그래프에 전달한다.
    state: GraphState = dict(initial_state)
    request_id = state.get("_request_id")
    if not isinstance(request_id, str) or not request_id:
        request_id = uuid.uuid4().hex
    state["_request_id"] = request_id
    started_ms = state.get("_started_ms")
    if not isinstance(started_ms, int):
        started_ms = int(time.time() * 1000)
    state["_started_ms"] = started_ms
    _log_mem(state, "start")

    query = state.get("query")
    user_input = state.get("user_input")

    # query가 비어 있으면 user_input을 그대로 검색 질의로 재사용한다.
    if (not isinstance(query, str) or not query.strip()) and isinstance(user_input, str):
        if user_input.strip():
            state["query"] = user_input

    # 검색 개수는 미지정 시 5개를 기본값으로 사용한다.
    if "retrieval_top_k" not in state:
        state["retrieval_top_k"] = 5
    top_k = state.get("retrieval_top_k")
    if isinstance(top_k, int) and top_k > 5:
        state["retrieval_top_k"] = 5

    # 컴파일된 그래프를 실행한다.
    result = get_compiled_graph().invoke(state)
    if not isinstance(result, dict):
        raise ValueError("compiled graph returned non-dict result")
    if "_request_id" not in result:
        result["_request_id"] = state["_request_id"]
    if "_started_ms" not in result:
        result["_started_ms"] = state["_started_ms"]
    _log_mem(result, "end")
    result.pop("_request_id", None)
    result.pop("_started_ms", None)
    return result


__all__ = [
    "build_graph",
    "get_compiled_graph",
    "run_job_search_graph",
]

def get_graph_mermaid() -> str:
    """
    컴파일된 그래프를 Mermaid 다이어그램 문자열로 반환한다.
    """
    # 실행 시 쓰는 컴파일 그래프를 재사용해 다이어그램과 실제 노드 연결이 어긋나지 않게 한다.
    compiled = get_compiled_graph()
    graph = compiled.get_graph()

    # Mermaid 문자열을 그대로 반환하면 CLI/문서/테스트에서 동일 출력 포맷을 재활용할 수 있다.
    return graph.draw_mermaid()


if __name__ == "__main__":
    # uv run python -m src.graph
    # 모듈 단독 실행 시 다이어그램 텍스트를 바로 확인할 수 있도록 stdout으로 출력한다.
    print(get_graph_mermaid())
