import random
import string

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lobby, LobbyMembership, Match
from .serializers import (
    JoinLobbySerializer,
    LobbySerializer,
)


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
