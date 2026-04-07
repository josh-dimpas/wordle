import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
import jwt


class WordleConsumer(AsyncWebsocketConsumer):
    user = None
    user_id = None

    async def connect(self):
        token = self.scope.get("query_string", b"").decode()
        token = dict(x.split("=") for x in token.split("&") if "=" in x).get(
            "token", ""
        )

        if not token:
            await self.close()
            return

        self.user = await self.get_user_from_token(token)
        if not self.user:
            await self.close()
            return

        self.user_id = self.user.id
        await self.channel_layer.group_add(f"user:{self.user_id}", self.channel_name)

        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "user_id": self.user_id,
                }
            )
        )

    async def disconnect(self, close_code):
        if self.user_id:
            await self.channel_layer.group_discard(
                f"user:{self.user_id}", self.channel_name
            )
            await self.handle_disconnect()

    async def receive(self, text_data):
        if not self.user:
            return

        try:
            data = json.loads(text_data)
            event_type = data.get("type")
            payload = data.get("data", {})

            if event_type == "typing:update":
                await self.handle_typing_update(payload)
            elif event_type == "match:guess":
                await self.handle_match_guess(payload)
            elif event_type == "lobby:join":
                await self.handle_lobby_join(payload)
            elif event_type == "lobby:leave":
                await self.handle_lobby_leave(payload)
            elif event_type == "match:join":
                await self.handle_match_join(payload)
            elif event_type == "match:leave":
                await self.handle_match_leave(payload)
        except json.JSONDecodeError:
            pass

    async def group_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": event["event_type"],
                    "data": event["data"],
                }
            )
        )

    async def handle_typing_update(self, payload):
        match_id = payload.get("match_id")
        current_input = payload.get("current_input", "")

        if not match_id:
            return

        await self.channel_layer.group_send(
            f"match:{match_id}",
            {
                "type": "group_message",
                "event_type": "typing:update",
                "data": {
                    "username": self.user.username,
                    "current_input": current_input,
                },
            },
        )

    async def handle_match_guess(self, payload):
        match_id = payload.get("match_id")
        guess = payload.get("guess", "")

        if not match_id or not guess:
            return

        result = await self.process_match_guess(match_id, guess)
        if result:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "game:guess_result",
                        "data": result,
                    }
                )
            )

    async def handle_lobby_join(self, payload):
        lobby_code = payload.get("lobby_code")
        if lobby_code:
            await self.channel_layer.group_add(f"lobby:{lobby_code}", self.channel_name)

    async def handle_lobby_leave(self, payload):
        lobby_code = payload.get("lobby_code")
        if lobby_code:
            await self.channel_layer.group_discard(
                f"lobby:{lobby_code}", self.channel_name
            )

    async def handle_match_join(self, payload):
        match_id = payload.get("match_id")
        if match_id:
            await self.channel_layer.group_add(f"match:{match_id}", self.channel_name)

    async def handle_match_leave(self, payload):
        match_id = payload.get("match_id")
        if match_id:
            await self.channel_layer.group_discard(
                f"match:{match_id}", self.channel_name
            )

    async def handle_disconnect(self):
        pending_match = await self.get_pending_match()
        if pending_match:
            await self.cancel_pending_match(pending_match)

        lobby = await self.get_current_lobby()
        if lobby:
            await self.leave_lobby(lobby)

    @database_sync_to_async
    def get_pending_match(self):
        from match_making.models import Match

        return (
            Match.objects.filter(players=self.user_id, status="pending")
            .annotate(player_count=Count("players"))
            .filter(player_count=1)
            .first()
        )

    @database_sync_to_async
    def cancel_pending_match(self, match):
        from match_making.models import Match, Lobby
        from websocket.services import WebSocketService

        Lobby.objects.filter(players=self.user_id, has_started=True).update(
            has_started=False
        )
        match_id = match.id
        match.delete()
        WebSocketService.send_to_user(
            self.user_id, "match:cancelled", {"match_id": match_id}
        )

    @database_sync_to_async
    def get_current_lobby(self):
        from match_making.models import Lobby

        return Lobby.objects.filter(players=self.user_id).first()

    @database_sync_to_async
    def leave_lobby(self, lobby):
        from match_making.models import LobbyMembership
        from websocket.services import WebSocketService

        lobby_code = lobby.code
        new_owner = None
        if lobby.owner_id == self.user_id and lobby.players.count() > 1:
            new_owner = lobby.players.exclude(id=self.user_id).first()
        LobbyMembership.objects.filter(lobby=lobby, player_id=self.user_id).delete()
        lobby.refresh_from_db()
        if lobby.players.count() == 0:
            lobby.delete()
        else:
            if lobby.owner_id == self.user_id and new_owner:
                lobby.owner = new_owner
                lobby.save()
            WebSocketService.broadcast_to_lobby(
                lobby_code,
                "lobby:player_left",
                {
                    "username": self.user.username,
                    "new_owner": new_owner.username if new_owner else None,
                },
            )

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            User = get_user_model()
            user = User.objects.filter(id=payload.get("user_id")).first()
            return user
        except jwt.InvalidTokenError, jwt.ExpiredSignatureError:
            return None

    @database_sync_to_async
    def process_match_guess(self, match_id, guess):
        from match_making.models import Match, MatchPlayer, MatchGame
        from game.models import Game
        from game.serializers import GameSerializer
        from asgiref.sync import sync_to_async

        match = Match.objects.filter(id=match_id).first()
        if not match or match.status != "active":
            return None

        if not match.players.filter(id=self.user_id).exists():
            return None

        match_player = MatchPlayer.objects.filter(
            match=match, player_id=self.user_id
        ).first()
        if not match_player:
            return None

        active_game = MatchGame.objects.filter(
            match=match,
            player_id=self.user_id,
            word_index=match_player.current_word_index,
            is_active=True,
        ).first()

        if not active_game:
            return None

        game = Game.objects.filter(id=active_game.game_id).first()
        if not game or game.get_is_finished():
            return None

        if len(guess) != len(game.word):
            return {"error": f"Word must be {len(game.word)} letters"}

        game.guess(guess)
        serializer = GameSerializer(game)

        return {
            "username": self.user.username,
            "guess": guess,
            "correct": game.word == guess,
            "game": serializer.data,
        }
