"""
Backward-compatible shim for entity normalization helpers.

Source of truth:
- normalize node: src.node
- utility functions: src.tools.slices.url_exchanger
"""

from src.node import normalize_and_validate_entities as normalize_and_validate_entities_node
from src.tools.slices.url_exchanger import (
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
    result = normalize_and_validate_entities_node({"entities": entities})
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
