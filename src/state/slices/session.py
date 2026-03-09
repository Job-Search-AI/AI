from typing import TypedDict


class SessionState(TypedDict, total=False):
    user_input: str
    follow_up_input: str
    query: str
    conversation_id: str
