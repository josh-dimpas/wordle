import random
import string
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from game.models import Game
from game.services import WordService
from game.serializers import GameSerializer

from .models import Lobby, LobbyMembership, Match, MatchPlayer, MatchGame
from .serializers import (
    JoinLobbySerializer,
    LobbySerializer,
    MatchSerializer,
)
from game.utils import config
from websocket.services import WebSocketService
from .utils import complete_match, advance_word, broadcast_guess_result


def generate_lobby_code():
    while True:
        letters = "".join(random.choices(string.ascii_lowercase, k=4))
        numbers = "".join(random.choices(string.digits, k=4))
        code = f"{letters}-{numbers}"
        if not Lobby.objects.filter(code=code).exists():
            return code


class LobbyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        existing_lobby = Lobby.objects.filter(players=request.user).first()
        if existing_lobby:
            existing_lobby.remove_player(request.user)

        code = generate_lobby_code()
        lobby = Lobby.objects.create(owner=request.user, code=code)
        LobbyMembership.objects.create(lobby=lobby, player=request.user)

        serializer = LobbySerializer(lobby, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LobbyJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = JoinLobbySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data["code"]
        lobby = Lobby.objects.filter(code=code).first()

        if lobby is None:
            return Response(
                {"error": "Lobby not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if lobby.has_started:
            return Response(
                {"error": "Lobby has already started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lobby.players.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are already in this lobby"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_lobby = Lobby.objects.filter(players=request.user).first()
        if existing_lobby:
            existing_lobby.remove_player(request.user)

        LobbyMembership.objects.create(lobby=lobby, player=request.user)

        WebSocketService.broadcast_to_lobby(
            lobby.code,
            "lobby:player_joined",
            {
                "username": request.user.username,
                "players": lobby.players.values_list("username", flat=True),
            },
        )

        serializer = LobbySerializer(lobby, context={"request": request})
        return Response(serializer.data)


class LobbyLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lobby = Lobby.objects.filter(players=request.user).first()

        if lobby is None:
            return Response(
                {"error": "You are not in any lobby"}, status=status.HTTP_404_NOT_FOUND
            )

        lobby_code = lobby.code
        new_owner = None
        if lobby.owner == request.user and lobby.players.count() > 1:
            new_owner = lobby.players.exclude(id=request.user.id).first()

        lobby.remove_player(request.user)

        WebSocketService.broadcast_to_lobby(
            lobby_code,
            "lobby:player_left",
            {
                "username": request.user.username,
                "new_owner": new_owner.username if new_owner else None,
            },
        )

        return Response({"message": "Left lobby successfully"})


class LobbyCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lobby = (
            Lobby.objects.filter(players=request.user)
            .prefetch_related("memberships__player")
            .first()
        )

        if lobby is None:
            return Response(
                {"message": "You are not in any lobby"}, status=status.HTTP_200_OK
            )

        serializer = LobbySerializer(lobby, context={"request": request})
        return Response(serializer.data)


class LobbyReadyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lobby = Lobby.objects.filter(players=request.user).first()

        if lobby is None:
            return Response(
                {"error": "You are not in any lobby"}, status=status.HTTP_404_NOT_FOUND
            )

        if lobby.has_started:
            return Response(
                {"error": "Lobby has already started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = lobby.memberships.filter(player=request.user).first()
        if membership:
            membership.is_ready = not membership.is_ready
            membership.save()

            WebSocketService.broadcast_to_lobby(
                lobby.code,
                "lobby:ready_toggled",
                {"username": request.user.username, "is_ready": membership.is_ready},
            )

        serializer = LobbySerializer(lobby, context={"request": request})
        return Response(serializer.data)


class LobbyStartView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        lobby = Lobby.objects.filter(players=request.user).first()

        if lobby is None:
            return Response(
                {"error": "You are not in any lobby"}, status=status.HTTP_404_NOT_FOUND
            )

        if lobby.owner != request.user:
            return Response(
                {"error": "Only the lobby owner can start the match"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if lobby.has_started:
            return Response(
                {"error": "Lobby has already started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        all_ready = (
            lobby.memberships.filter(is_ready=True).count() == lobby.players.count()
        )
        if not all_ready:
            return Response(
                {"error": "Not all players are ready"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lobby.players.count() < 2:
            return Response(
                {"error": "Need at least 2 players to start"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lobby.has_started = True
        lobby.save()

        match = Match.objects.create(lobby=lobby, status="active")
        match.players.set(lobby.players.all())

        num_players = lobby.players.count()
        words_per_player = config.MULTIPLAYER_LIVES * num_players

        for membership in lobby.memberships.all():
            membership.is_ready = False
            membership.save()

            MatchPlayer.objects.create(
                match=match,
                player=membership.player,
                lives=config.MULTIPLAYER_LIVES,
                current_word_index=0,
            )

            words = WordService.get_random_words(words_per_player)
            for i, word in enumerate(words):
                game = Game.objects.create(
                    word=word,
                    player=membership.player,
                )
                MatchGame.objects.create(
                    match=match,
                    player=membership.player,
                    word_index=i,
                    is_active=(i == 0),
                    game_id=game.pk,
                )

        WebSocketService.broadcast_to_lobby(
            lobby.code, "lobby:started", {"match_id": match.pk}
        )

        serializer = MatchSerializer(match)
        return Response(serializer.data)


class MatchStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id):
        match = Match.objects.filter(id=match_id).first()

        if match is None:
            return Response(
                {"error": "Match not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not match.players.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not in this match"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = MatchSerializer(match)
        return Response(serializer.data)


class MatchGuessView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, match_id, input):
        match = Match.objects.filter(id=match_id).first()
        if not match:
            return Response(
                {"error": "Match not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if match.status != "active":
            return Response(
                {"error": "Match is not active"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not match.players.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not in this match"}, status=status.HTTP_403_FORBIDDEN
            )

        match_player = MatchPlayer.objects.filter(
            match=match, player=request.user
        ).first()
        if not match_player:
            return Response(
                {"error": "Player not found in match"}, status=status.HTTP_404_NOT_FOUND
            )

        active_game = MatchGame.objects.filter(
            match=match,
            player=request.user,
            word_index=match_player.current_word_index,
            is_active=True,
        ).first()
        if not active_game:
            return Response(
                {"error": "No active game found"}, status=status.HTTP_400_BAD_REQUEST
            )

        game = Game.objects.filter(id=active_game.game_id).first()
        if not game:
            return Response(
                {"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if game.get_is_finished():
            return Response(
                {"error": "Game already finished"}, status=status.HTTP_400_BAD_REQUEST
            )

        if len(input) != len(game.word):
            return Response(
                {
                    "error": f"Please provide a word with matching length. You sent {len(input)}, required is {len(game.word)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        game.guess(input)

        if game.word == input:
            return self._handle_correct_guess(
                match, match_player, active_game, game, request.user
            )

        if game.get_tries_left() == 0:
            return self._handle_no_tries_left(
                match, match_player, active_game, game, request.user
            )

        broadcast_guess_result(match, request.user.username, input, False)
        return Response(GameSerializer(game).data)

    def _handle_correct_guess(self, match, match_player, active_game, game, player):
        active_game.is_active = False
        active_game.save()

        opponent_lives_after = {}
        for opponent in MatchPlayer.objects.filter(match=match).exclude(player=player):
            opponent.lives = F("lives") - 1
            opponent.save()
            opponent.refresh_from_db()
            opponent_lives_after[opponent.player.pk] = opponent.lives

        remaining_players = MatchPlayer.objects.filter(match=match, lives__gt=0)
        if remaining_players.count() == 1:
            complete_match(match, remaining_players.first().player)
            WebSocketService.broadcast_to_match(
                match.id,
                "match:completed",
                {
                    "winner_username": match.winner.username,
                    "winner_id": match.winner.id,
                },
            )
        else:
            advance_word(match_player, match, player)
            WebSocketService.broadcast_to_match(
                match.id,
                "game:opponent_word_advanced",
                {
                    "username": player.username,
                    "word_index": match_player.current_word_index,
                    "lives": match_player.lives,
                },
            )

        broadcast_guess_result(
            match, player.username, input, True, opponent_lives=opponent_lives_after
        )
        return Response(
            {
                "message": "Correct! Opponent lost a life.",
                "game": GameSerializer(game).data,
            }
        )

    def _handle_no_tries_left(self, match, match_player, active_game, game, player):
        active_game.is_active = False
        active_game.save()

        match_player.lives = F("lives") - 1
        match_player.save()
        match_player.refresh_from_db()

        if match_player.lives <= 0:
            remaining_players = MatchPlayer.objects.filter(match=match, lives__gt=0)
            if remaining_players.exists():
                complete_match(match, remaining_players.first().player)
                WebSocketService.broadcast_to_match(
                    match.id,
                    "match:completed",
                    {
                        "winner_username": match.winner.username,
                        "winner_id": match.winner.id,
                    },
                )
            else:
                complete_match(match)
                WebSocketService.broadcast_to_match(
                    match.id,
                    "match:completed",
                    {"winner_username": None, "winner_id": None},
                )
        else:
            advance_word(match_player, match, player)
            WebSocketService.broadcast_to_match(
                match.id,
                "game:opponent_word_advanced",
                {
                    "username": player.username,
                    "word_index": match_player.current_word_index,
                    "lives": match_player.lives,
                },
            )

        broadcast_guess_result(match, player.username, input, False, word=game.word)
        return Response(
            {
                "message": f"Ran out of tries. Word was {game.word}.",
                "game": GameSerializer(game).data,
            }
        )


class MatchGetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        existing_match = Match.objects.filter(
            players=request.user, status__in=["pending", "active"]
        ).first()

        if existing_match:
            return Response(MatchSerializer(existing_match), status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)


class MatchFindView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        existing_match = Match.objects.filter(
            players=request.user, status__in=["pending", "active"]
        ).first()
        if existing_match:
            return Response(
                {
                    "error": "You are already in a match",
                    "match": MatchSerializer(existing_match).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        timeout_minutes = config.PENDING_MATCH_TIMEOUT_MINUTES
        stale_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
        Match.objects.filter(status="pending", created_at__lt=stale_threshold).delete()

        pending_match = (
            Match.objects.filter(status="pending")
            .annotate(player_count=Count("players"))
            .filter(player_count=1)
            .first()
        )

        if pending_match:
            pending_match.players.add(request.user)
            MatchPlayer.objects.create(
                match=pending_match,
                player=request.user,
                lives=config.MULTIPLAYER_LIVES,
                current_word_index=0,
            )

            num_players = 2
            words_per_player = config.MULTIPLAYER_LIVES * num_players

            existing_player = pending_match.match_players.exclude(
                player=request.user
            ).first()
            if existing_player:
                existing_player.current_word_index = 0
                existing_player.save()

            for player in pending_match.players.all():
                existing_games = MatchGame.objects.filter(
                    match=pending_match, player=player
                ).exists()
                if not existing_games:
                    words = WordService.get_random_words(words_per_player)
                    for i, word in enumerate(words):
                        game = Game.objects.create(word=word, player=player)
                        MatchGame.objects.create(
                            match=pending_match,
                            player=player,
                            word_index=i,
                            is_active=(i == 0),
                            game_id=game.pk,
                        )

            pending_match.status = "active"
            pending_match.save()

            for player in pending_match.players.all():
                WebSocketService.send_to_user(
                    player.pk,
                    "match:opponent_found",
                    {
                        "match_id": pending_match.pk,
                        "status": "active",
                        "players": list(
                            pending_match.players.values_list("username", flat=True)
                        ),
                    },
                )

            serializer = MatchSerializer(pending_match)
            return Response(
                {**serializer.data, "message": "Match started!"},
            )

        match = Match.objects.create(status="pending")
        match.players.add(request.user)
        MatchPlayer.objects.create(
            match=match,
            player=request.user,
            lives=config.MULTIPLAYER_LIVES,
            current_word_index=0,
        )

        serializer = MatchSerializer(match)
        return Response(
            {**serializer.data, "message": "Waiting for opponent..."},
            status=status.HTTP_201_CREATED,
        )


class MatchCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        match = Match.objects.filter(
            players=request.user, status__in=["pending", "active"]
        ).first()

        if not match:
            return Response(
                {"error": "No cancellable match found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        Lobby.objects.filter(players=request.user, has_started=True).update(
            has_started=False
        )

        match_id = match.pk
        match.delete()

        WebSocketService.send_to_user(
            request.user.id, "match:cancelled", {"match_id": match_id}
        )

        return Response({"message": "Match cancelled successfully"})
