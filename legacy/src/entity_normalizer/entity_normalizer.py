"""
엔티티 정규화 helper를 기존 호출 방식과 함께 제공한다.

Source of truth:
- normalize node: src.node
- utility functions: src.tools.slices.entity_normalizer
"""

from src.node import normalize_and_validate_entities as normalize_and_validate_entities_node
from src.tools.slices.entity_normalizer import (
    check_missing_entities,
    generate_missing_message,
    load_synonym_dict,
    normalize_entities,
    normalize_entity_value,
)


def normalize_and_validate_entities(entities):
    """
    Legacy tuple API wrapper.
    """
    # node 함수는 dict 기반 상태를 받으므로, 기존 엔티티 입력을 상태 형태로 감싸서 전달한다.
    result = normalize_and_validate_entities_node({"entities": entities})
    # 상위 호출부가 기존 tuple 포맷을 사용하고 있어 동일한 순서로 반환한다.
    return (
        result["status"],
        result["message"],
        result["missing_fields"],
        result["normalized_entities"],
    )


__all__ = [
    "load_synonym_dict",
    "normalize_entity_value",
    "normalize_entities",
    "check_missing_entities",
    "generate_missing_message",
    "normalize_and_validate_entities_node",
    "normalize_and_validate_entities",
]
