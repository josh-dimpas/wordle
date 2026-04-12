# Just a plain event, not emitted by the user
from websocket.consumers import WordleConsumer


async def event(stub: WordleConsumer):
    user = stub.user

    # Get existing matches of the user

    # Cancel/Complete existing match

    # Get existing lobbies of the user

    # Notify the other parties
