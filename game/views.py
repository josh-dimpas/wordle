from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Game
from .serializers import (
    GameCreateSerializer,
    GameSerializer,
    GameSummarySerializer,
)
from .services import WordService


class IndexView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "message": (
                    "Welcome to wordle API. "
                    "Login your account with /login. "
                    "Don't have an account yet? try /register."
                )
            }
        )


class PlayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.user.username

        game = Game.objects.create(
            word=WordService.get_random_word(),
            player=username,
        )

        serializer = GameCreateSerializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ViewGameView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        username = request.user.username
        game = Game.objects.filter(id=game_id).first()

        if game is None:
            return Response(
                {"error": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if game.player != username:
            return Response(
                {"error": f"{username} does not own this game"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GameSerializer(game)
        return Response(serializer.data)


class GuessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, game_id: str, input: str):
        username = request.user.username
        game = Game.objects.filter(id=game_id).first()

        if game is None:
            return Response(
                {"error": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        if game.player != username:
            return Response(
                {"error": f"{username} does not own this game"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if len(input) != len(game.word):
            return Response(
                {
                    "error": f"Please provide a word with matching length. You sent {len(input)}, required is {len(game.word)}"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if game.is_win:
            return Response({"message": f"Game has already won. Word is {game.word}."})

        if game.get_is_finished():
            return Response({"message": f"You ran out of tries. Word is {game.word}."})

        game.guess(input)

        if game.word == input:
            return Response(
                {"message": f"You guessed correctly in just {len(game.tries)} tries! "}
            )

        if game.get_tries_left() == 0:
            return Response({"message": f"You ran out of tries. Word is {game.word}"})

        serializer = GameSerializer(game)
        return Response(serializer.data)


class AccountStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        username = request.user.username

        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", "10"))
        order = request.query_params.get("order", "desc")
        is_descending = order == "desc"

        games = Game.objects.filter(player=username).order_by(
            "-created_at" if is_descending else "created_at"
        )[offset : offset + limit]

        won_games = [obj for obj in games if obj.is_win]

        games_data = GameSummarySerializer(games, many=True).data

        return Response(
            {
                "games_played": len(games),
                "games_won": len(won_games),
                "games": games_data,
            }
        )


class LeaderboardsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        offset = int(request.query_params.get("offset", "0"))
        limit = max(1, min(50, int(request.query_params.get("limit", "10"))))
        order = request.query_params.get("order", "desc")
        is_descending = order == "desc"

        players = (
            Game.objects.values("player")
            .annotate(
                games_won=Count("id", filter=Q(is_win=True)),
                games_played=Count("id"),
            )
            .order_by("-games_won" if is_descending else "games_won")[
                offset : offset + limit
            ]
        )

        return Response(players)
