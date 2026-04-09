import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import jwt

from users.models import Account
from users.utils import config


class WordleConsmer(AsyncWebsocketConsumer):
    user: Account 

    async def connect(self):
        query = self.scope.get("query_string", b"").decode()
        token = (
            dict(x.split("=") for x in query.split("&") if "=" in x)
            .get( "token", "")
        )

        if not token:
            await self.close()
            return

    async def disconnect(self, code: int) -> None:
        return await super().disconnect(code)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is None:
            return
        text_data_json = json.loads(text_data)
        message = text_data_json['data']
        return await super().receive(text_data, bytes_data)


    # Utils
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, config.JWT_KEY, algorithms=["HS256"])
            user = Account.objects.filter(id=payload.get("user_id")).first()
            return user
        except jwt.InvalidTokenError, jwt.ExpiredSignatureError:
            return None
