from typing import Any, TypedDict

from websocket.consumers import WordleConsumer


class GuessEventPayload(TypedDict):
    user_id: int
    match_id: int
    word: str


async def guess(stub: WordleConsumer, data: Any):
    payload: GuessEventPayload = data
