import json
import jwt

from typing import Any
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken

from users.models import Account
from .events import match
from .events import typing


class WordleConsumer(AsyncWebsocketConsumer):
    user: Account | None

    async def connect(self):
        query = self.scope.get("query_string", b"").decode()
        token = dict(x.split("=") for x in query.split("&") if "=" in x).get(
            "token", ""
        )

        print(token)

        if not token:
            await self.close(reason="Token not found")
            return

        user = await self.get_user_from_token(token)
        self.user = user

        if not user:
            await self.close(reason="Token invalid")
            return

        await self.accept()
        await self.send({"type": "connection-success", "data": {"user-id": user.pk}})

    async def disconnect(self, code: int) -> None:
        return await super().disconnect(code)

    async def receive(
        self, text_data: str | None = "", bytes_data: bytes | None = None
    ) -> None:
        assert isinstance(text_data, str), "Empty websocket signal data"

        text_data = text_data.strip()
        payload: dict = json.loads(text_data)

        type = payload.get("type")
        data = payload.get("data")

        if type is None:
            await self.send({"details": "No event-type passed"})
            return

        # TODO: Find said event using a file-based command mapper
        # Manually do a switch case for now
        try:
            await self.handle(type, data)
        except Exception:
            await self.send({"details": "Event type invalid"})

    async def send(self, obj: Any):  # type: ignore
        payload = json.dumps(obj)
        await super().send(text_data=payload)

    # Utils
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            payload = AccessToken(token)
            user = Account.objects.filter(id=payload["user_id"]).first()
            return user
        except jwt.InvalidTokenError, jwt.ExpiredSignatureError:
            return None

    @database_sync_to_async
    async def handle(self, type: str, data: Any):
        match type:
            case "match:guess":
                await match.guess(self, data)
            case "typing:update":
                await typing.update(self, data)

            case _:
                raise Exception(f"Event type [{type}] is unimplemented")
