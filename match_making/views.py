import random
import string

from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from game.models import Game
from game.services import WordService
from game.serializers import GameSerializer
from django.apps import apps

from .models import Lobby, LobbyMembership, Match, MatchPlayer, MatchGame
from .serializers import (
    JoinLobbySerializer,
    LobbySerializer,
    MatchSerializer,
    MatchGuessSerializer,
)

config = apps.get_app_config("game")


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

        existing_lobby = Lobby.objects.filter(players=request.user).first()
        if existing_lobby:
            existing_lobby.remove_player(request.user)

        if lobby.players.filter(id=request.user.id).exists():
            return Response({"error": "You are already in this lobby"})

        LobbyMembership.objects.create(lobby=lobby, player=request.user)

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

        lobby.remove_player(request.user)
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
                    game_id=game.id,
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
