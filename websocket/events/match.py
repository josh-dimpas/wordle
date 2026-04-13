from __future__ import annotations
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from websocket.consumers import WordleConsumer


class GuessEventPayload(TypedDict):
    user_id: int
    match_id: int
    word: str


async def guess(stub: WordleConsumer, data: Any):
    payload: GuessEventPayload = data
