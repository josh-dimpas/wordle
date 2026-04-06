from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from match_making.models import Match, MatchPlayer
from .models import Game
from .serializers import (
    GameCreateSerializer,
    GameSerializer,
    LeaderboardSerializer,
    MatchHistorySerializer,
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
        game = Game.objects.create(
            word=WordService.get_random_word(),
            player=request.user,
        )

        serializer = GameCreateSerializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ViewGameView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        game = Game.objects.filter(id=game_id, player=request.user).first()

        if game is None:
            return Response(
                {"error": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = GameSerializer(game)
        return Response(serializer.data)


class GuessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, game_id: str, input: str):
        game = Game.objects.filter(id=game_id, player=request.user).first()

        if game is None:
            return Response(
                {"error": "Game does not exist"}, status=status.HTTP_404_NOT_FOUND
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
        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", "10"))
        order = request.query_params.get("order", "desc")
        is_descending = order == "desc"

        matches = Match.objects.filter(players=request.user).order_by(
            "-created_at" if is_descending else "created_at"
        )[offset : offset + limit]

        matches_data = []
        for match in matches:
            opponent = match.players.exclude(id=request.user.id).first()
            matches_data.append(
                {
                    "game_id": match.id,
                    "won": match.winner == request.user,
                    "opponent": opponent.username if opponent else None,
                    "opponent_id": opponent.id if opponent else None,
                    "date": match.created_at,
                }
            )

        serializer = MatchHistorySerializer(matches_data, many=True)

        return Response(
            {
                "matches_played": request.user.matches_count,
                "matches_won": request.user.wins,
                "matches": serializer.data,
            }
        )


class LeaderboardsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from users.models import Account

        offset = int(request.query_params.get("offset", "0"))
        limit = max(1, min(50, int(request.query_params.get("limit", "10"))))
        order = request.query_params.get("order", "desc")
        is_descending = order == "desc"

        players = (
            Account.objects.filter(matches_count__gt=0)
            .values("username", "wins", "matches_count")
            .order_by("-wins" if is_descending else "wins")[offset : offset + limit]
        )

        serializer = LeaderboardSerializer(players, many=True)
        return Response(serializer.data)
