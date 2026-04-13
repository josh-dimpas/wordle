# Just a plain event, not emitted by the user
from __future__ import annotations

from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from websocket.consumers import WordleConsumer


async def event(stub: WordleConsumer):
    user = stub.user

    # Get existing matches of the user

    # Cancel/Complete existing match

    # Get existing lobbies of the user

    # Notify the other parties
