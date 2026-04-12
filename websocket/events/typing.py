from typing import Any, TypedDict

from websocket.consumers import WordleConsumer


class TypeUpdatePayload(TypedDict):
    user_id: int
    match_id: int
    word: str


async def update(stub: WordleConsumer, data: Any):
    payload: TypeUpdatePayload = data
