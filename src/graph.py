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


def build_graph() -> StateGraph:
    # 그래프는 노드 연결 규칙을 한 곳에 모아, 파이프라인 흐름을 코드로 명시한다.
    workflow = StateGraph(GraphState)

    # 노드명은 디버깅/트레이싱 시 그대로 보이므로 역할 중심으로 단순하게 고정한다.
    workflow.add_node("singleton_model", singleton_model_node)
    workflow.add_node("predict_entities", predict_crf_bert)
    workflow.add_node("normalize_entities", normalize_and_validate_entities)
    workflow.add_node("map_url", mapping_url_query_node)
    workflow.add_node("crawl_html", crawl_job_html_from_saramin)
    workflow.add_node("parse_job_info", parse_job_info_node)
    workflow.add_node("search_hybrid", search_hybrid_retriever_node)
    workflow.add_node("generate_user_response", generate_user_response_node)

    # 메인 플로우는 모델 준비 -> 엔티티 추출/정규화까지 직렬로 진행한다.
    workflow.add_edge(START, "singleton_model")
    workflow.add_edge("singleton_model", "predict_entities")
    workflow.add_edge("predict_entities", "normalize_entities")

    # 정규화 결과는 라우터가 검사하고, 정보 부족이면 즉시 종료한다.
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
    global _COMPILED_GRAPH

    # 컴파일은 비용이 있으므로 프로세스 내에서 한 번만 수행해 재사용한다.
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph().compile()
    return _COMPILED_GRAPH


def run_job_search_graph(initial_state: Mapping[str, Any]) -> GraphState:
    # 실행 진입점은 외부 입력을 받아 최소 기본값(query, top_k)만 보정한다.
    if not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be a mapping")

    # 입력 원본을 직접 바꾸지 않기 위해 복사본을 만들어 그래프에 전달한다.
    state: GraphState = dict(initial_state)
    query = state.get("query")
    user_input = state.get("user_input")

    # query가 비어 있으면 user_input을 그대로 검색 질의로 재사용한다.
    if (not isinstance(query, str) or not query.strip()) and isinstance(user_input, str):
        if user_input.strip():
            state["query"] = user_input

    # 검색 개수는 호출부 미지정 시 기존 계획대로 5개를 기본값으로 사용한다.
    if "retrieval_top_k" not in state:
        state["retrieval_top_k"] = 5

    result = get_compiled_graph().invoke(state)
    if not isinstance(result, dict):
        raise ValueError("compiled graph returned non-dict result")
    return result


__all__ = [
    "build_graph",
    "get_compiled_graph",
    "run_job_search_graph",
]
