from typing import Any, TypedDict


class ParsingState(TypedDict, total=False):
    job_info_list: list[str]
    job_metadata_list: list[dict[str, Any]]
