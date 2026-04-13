from __future__ import annotations

from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from websocket.consumers import WordleConsumer


class TypeUpdatePayload(TypedDict):
    user_id: int
    match_id: int
    word: str


async def update(stub: WordleConsumer, data: Any):
    payload: TypeUpdatePayload = data

    # Do nothing for now (linter disapproves)
    stub.send({"message": f"Successfully updated {payload['word']}"})
