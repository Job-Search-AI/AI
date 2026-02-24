from typing import TypedDict


class LlmState(TypedDict, total=False):
    user_response: str
    error: str | None
