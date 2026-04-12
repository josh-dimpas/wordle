import json
import jwt

from typing import Any
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken

from users.models import Account


class WordleConsumer(AsyncWebsocketConsumer):
    user: Account | None

    async def connect(self):
        query = self.scope.get("query_string", b"").decode()
        token = dict(x.split("=") for x in query.split("&") if "=" in x).get(
            "token", ""
        )

        print(token)

        if not token:
            await self.close(code=4001)
            return

        user = await self.get_user_from_token(token)
        self.user = user

        if not user:
            await self.close(code=4001)
            return

        await self.accept()
        await self.send({"type": "connection-success", "data": {"user-id": user.pk}})

    async def disconnect(self, code: int) -> None:
        return await super().disconnect(code)

    async def receive(
        self, text_data: str | None = None, bytes_data: bytes | None = None
    ) -> None:
        text_data = text_data.strip()

        if text_data is None or text_data == "":
            text_data = "{}"

        payload: dict = json.loads(text_data)

        event = payload.get("type")
        data = payload.get("data")

        if event is None:
            await self.send({"details": "No event-type passed"})
            return

        # Manually do a switch case

        # TODO: Find said event using the file-based command mapper
        event_runner = WordleConsumer.events.get(event)

        if event_runner is None:
            print("NO EVENT RUNNER")
        else:
            print("EVENT RUNNER THERE IS")

        return await super().receive(text_data, bytes_data)

    async def send(self, obj: Any):
        payload = json.dumps(obj)
        await super().send(text_data=payload)

    # Utils
    @database_sync_to_async
    def get_user_from_token(self, token: str):
        try:
            payload = AccessToken(token)
            user = Account.objects.filter(id=payload["user_id"]).first()
            return user
        except jwt.InvalidTokenError, jwt.ExpiredSignatureError:
            return None
