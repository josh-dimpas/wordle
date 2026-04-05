from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Game
from .serializers import (
    AccountStatsSerializer,
    GameCreateSerializer,
    GameSerializer,
    GameSummarySerializer,
)
from .services import WordService
from .utils import config


class IndexView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "message": (
                    "Welcome to wordle API. "
                    "Login your account with /login. "
                    "Don't have an account yet? try /register. "
                    f"Start a game immediately now with /{config.ANON_USERNAME}/play"
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

    def post(self, request, game_id):
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

        input_word = request.data.get("input") or request.query_params.get("input")
        if not input_word:
            return Response(
                {"error": "Missing 'input' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(input_word) != len(game.word):
            return Response(
                {
                    "error": f"Please provide a word with matching length. You sent {len(input_word)}, required is {len(game.word)}"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if game.is_win:
            return Response({"message": f"Game has already won. Word is {game.word}."})

        if game.get_is_finished():
            return Response({"message": f"You ran out of tries. Word is {game.word}."})

        game.guess(input_word)

        if game.word == input_word:
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

        if username == config.ANON_USERNAME:
            return Response({"message": "No stats for anon"})

        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", "10"))
        order = request.query_params.get("order", "desc")
        is_descending = order == "desc"

        games = Game.objects.filter(player=username).order_by(
            f"-created_at" if is_descending else "created_at"
        )[offset : offset + limit]

        won_games = [obj for obj in games if obj.is_win]

        games_data = GameSummarySerializer(
            [
                {
                    "id": g.id,
                    "won": g.is_win,
                    "tries_left": g.get_tries_left(),
                    "created_at": g.created_at,
                }
                for g in games
            ],
            many=True,
        ).data

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

        query = f"""
        SELECT
            g.player,
            COUNT(CASE WHEN g.is_win = TRUE THEN 1 END) as games_won,
            COUNT(*) AS games_played
        FROM game_game AS g
        WHERE g.player != '{config.ANON_USERNAME}'
        GROUP BY g.player
        ORDER BY games_won {"DESC" if is_descending else "ASC"}
        LIMIT {limit}
        {"" if offset == 0 else f"OFFSET {offset}"}
        """

        with connection.cursor() as cursor:
            cursor.execute(query)

            if not cursor.description:
                return Response([], status=status.HTTP_200_OK)

            columns = [col[0] for col in cursor.description]
            players = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return Response(players)
