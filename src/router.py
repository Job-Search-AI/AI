from collections.abc import Mapping
from typing import Any

ROUTE_INCOMPLETE_END = "incomplete_end"
ROUTE_MAP_URL = "map_url"

REQUIRED_ENTITY_FIELDS = ("지역", "직무", "경력", "학력")


def route_after_normalize_entities(state: Mapping[str, Any]) -> str:
    # 이 라우터는 정규화 단계 결과를 보고 "정보 부족 종료"와 "URL 매핑" 중 다음 노드를 결정한다.
    # 상태가 비정상이어도 예외를 던지지 않고 안전하게 정보 부족 종료로 회귀시키는 것이 목적이다.
    if not isinstance(state, Mapping):
        return ROUTE_INCOMPLETE_END

    # 정규화 노드가 누락 정보를 감지하면 status="incomplete"를 반환하므로 우선순위를 가장 높게 둔다.
    if state.get("status") == "incomplete":
        return ROUTE_INCOMPLETE_END

    # missing_fields가 비어있지 않다면 필수 슬롯이 아직 부족하다는 의미이므로 재질문 분기로 보낸다.
    if state.get("missing_fields"):
        return ROUTE_INCOMPLETE_END

    # URL 매핑은 4개 필수 슬롯이 모두 채워져야 하므로 normalized_entities 형태와 값을 함께 검증한다.
    normalized_entities = state.get("normalized_entities")
    if not isinstance(normalized_entities, Mapping):
        return ROUTE_INCOMPLETE_END

    for field in REQUIRED_ENTITY_FIELDS:
        value = normalized_entities.get(field)

        # None, 빈 문자열, 문자열 이외 타입은 모두 불완전 입력으로 간주한다.
        if value is None:
            return ROUTE_INCOMPLETE_END
        if isinstance(value, str):
            if not value.strip():
                return ROUTE_INCOMPLETE_END
            continue
        return ROUTE_INCOMPLETE_END

    return ROUTE_MAP_URL


__all__ = [
    "ROUTE_INCOMPLETE_END",
    "ROUTE_MAP_URL",
    "REQUIRED_ENTITY_FIELDS",
    "route_after_normalize_entities",
]
