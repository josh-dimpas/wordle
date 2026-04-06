from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from match_making.models import Match
from .models import Game
from .serializers import GameSerializer, GameSummarySerializer, LeaderboardSerializer
from users.models import Account


class GameModelTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.game = Game.objects.create(player=self.user, word="hello")

    def test_game_creation(self):
        self.assertEqual(self.game.word, "hello")
        self.assertEqual(self.game.player, self.user)
        self.assertFalse(self.game.is_win)
        self.assertEqual(self.game.max_tries, 6)
        self.assertEqual(self.game.tries, [])

    def test_guess_correct_word(self):
        self.game.guess("hello")
        self.assertTrue(self.game.is_win)
        self.assertEqual(self.game.tries, ["hello"])

    def test_guess_wrong_word(self):
        self.game.guess("world")
        self.assertFalse(self.game.is_win)
        self.assertEqual(self.game.tries, ["world"])
        self.assertEqual(self.game.get_tries_left(), 5)

    def test_get_tries_left(self):
        self.assertEqual(self.game.get_tries_left(), 6)
        self.game.guess("world")
        self.assertEqual(self.game.get_tries_left(), 5)

    def test_get_is_finished_win(self):
        self.game.guess("hello")
        self.assertTrue(self.game.get_is_finished())

    def test_get_is_finished_no_tries_left(self):
        for _ in range(6):
            self.game.guess("wrong")
        self.assertTrue(self.game.get_is_finished())
        self.assertFalse(self.game.is_win)

    def test_assess_guess_exact(self):
        result = self.game.assess_guess("hello")
        self.assertIn("h/", result)
        self.assertIn("e/", result)
        self.assertIn("l/", result)

    def test_assess_guess_partial(self):
        result = self.game.assess_guess("world")
        self.assertIn("o+", result)

    def test_assess_guess_wrong(self):
        result = self.game.assess_guess("xyzjk")
        self.assertNotIn("/", result)
        self.assertNotIn("+", result)


class GameSerializerTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.game = Game.objects.create(player=self.user, word="hello")

    def test_game_serializer_fields(self):
        serializer = GameSerializer(self.game)
        data = serializer.data

        self.assertIn("id", data)
        self.assertIn("player", data)
        self.assertIn("tries_left", data)
        self.assertIn("tries", data)
        self.assertIn("word_length", data)
        self.assertIn("created_at", data)

        self.assertEqual(data["player"], "testuser")
        self.assertEqual(data["word_length"], 5)
        self.assertEqual(data["tries_left"], 6)
        self.assertEqual(data["tries"], [])

    def test_game_serializer_word_hidden_until_finished(self):
        serializer = GameSerializer(self.game)
        data = serializer.data
        self.assertIsNone(data["word"])

    def test_game_serializer_word_shown_when_finished(self):
        self.game.guess("hello")
        serializer = GameSerializer(self.game)
        data = serializer.data
        self.assertEqual(data["word"], "hello")

    def test_game_serializer_tries_with_assessment(self):
        self.game.guess("hells")
        serializer = GameSerializer(self.game)
        data = serializer.data
        self.assertEqual(len(data["tries"]), 1)
        self.assertIn("/", data["tries"][0])

    def test_game_summary_serializer_fields(self):
        serializer = GameSummarySerializer(self.game)
        data = serializer.data

        self.assertIn("id", data)
        self.assertIn("won", data)
        self.assertIn("tries_left", data)
        self.assertIn("created_at", data)


class LeaderboardSerializerTests(TestCase):
    def test_serializer_fields(self):
        data = {"username": "testuser", "wins": 5, "matches_count": 10}
        serializer = LeaderboardSerializer(data)
        result = serializer.data

        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["wins"], 5)
        self.assertEqual(result["matches_count"], 10)


class IndexViewTests(APITestCase):
    def test_index_returns_welcome_message(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("Welcome to wordle API", response.data["message"])


class PlayViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_play_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/play")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_play_creates_game(self):
        response = self.client.post("/play")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        game = Game.objects.get(id=response.data["id"])
        self.assertEqual(game.player, self.user)
        self.assertEqual(len(game.word), 5)

    def test_play_returns_game_id(self):
        response = self.client.post("/play")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)


class ViewGameViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.other_user = Account.objects.create_user(
            username="otheruser", password="testpass123"
        )
        self.game = Game.objects.create(player=self.user, word="hello")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_view_game_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(f"/game/{self.game.id}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_game_returns_game(self):
        response = self.client.get(f"/game/{self.game.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["player"], "testuser")
        self.assertEqual(response.data["word_length"], 5)

    def test_view_game_not_found(self):
        response = self.client.get("/game/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_other_users_game_forbidden(self):
        other_game = Game.objects.create(player=self.other_user, word="world")
        response = self.client.get(f"/game/{other_game.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GuessViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.game = Game.objects.create(player=self.user, word="hello")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_guess_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(f"/game/{self.game.id}/hello")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guess_correct_word(self):
        response = self.client.post(f"/game/{self.game.id}/hello")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("guessed correctly", response.data["message"])

    def test_guess_wrong_word(self):
        response = self.client.post(f"/game/{self.game.id}/world")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tries", response.data)
        self.assertEqual(len(response.data["tries"]), 1)

    def test_guess_wrong_length(self):
        response = self.client.post(f"/game/{self.game.id}/hi")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_guess_game_not_found(self):
        response = self.client.post("/game/99999/hello")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guess_already_won(self):
        self.game.guess("hello")
        response = self.client.post(f"/game/{self.game.id}/hello")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("already won", response.data["message"])

    def test_guess_exhausted_tries(self):
        for _ in range(6):
            self.client.post(f"/game/{self.game.id}/wrong")

        response = self.client.post(f"/game/{self.game.id}/world")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("ran out of tries", response.data["message"])


class AccountStatsViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123", wins=5, matches_count=10
        )
        self.game = Game.objects.create(player=self.user, word="hello")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_stats_requires_authentication(self):
        self.client.credentials()
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_returns_account_stats(self):
        response = self.client.get("/stats")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matches_played"], 10)
        self.assertEqual(response.data["matches_won"], 5)

    def test_stats_returns_matches_list(self):
        opponent = Account.objects.create_user(username="opponent", password="test")
        match = Match.objects.create(status="completed", winner=self.user)
        match.players.add(self.user, opponent)

        response = self.client.get("/stats")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("matches", response.data)
        self.assertEqual(len(response.data["matches"]), 1)

    def test_stats_pagination(self):
        opponent = Account.objects.create_user(username="opponent2", password="test")
        match1 = Match.objects.create(status="completed", winner=self.user)
        match1.players.add(self.user, opponent)
        match2 = Match.objects.create(status="completed", winner=opponent)
        match2.players.add(self.user, opponent)

        response = self.client.get("/stats?offset=0&limit=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["matches"]), 1)


class LeaderboardsViewTests(APITestCase):
    def setUp(self):
        self.user1 = Account.objects.create_user(
            username="player1", password="testpass123", wins=10, matches_count=20
        )
        self.user2 = Account.objects.create_user(
            username="player2", password="testpass123", wins=5, matches_count=15
        )

    def test_leaderboards_public_access(self):
        response = self.client.get("/leaderboards")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_leaderboards_returns_players(self):
        response = self.client.get("/leaderboards")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_leaderboards_sorted_by_wins_descending(self):
        response = self.client.get("/leaderboards")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["username"], "player1")
        self.assertEqual(response.data[0]["wins"], 10)

    def test_leaderboards_sorted_by_wins_ascending(self):
        response = self.client.get("/leaderboards?order=asc")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["username"], "player2")
        self.assertEqual(response.data[0]["wins"], 5)

    def test_leaderboards_excludes_zero_matches(self):
        Account.objects.create_user(
            username="newplayer", password="testpass123", wins=0, matches_count=0
        )
        response = self.client.get("/leaderboards")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_leaderboards_pagination(self):
        response = self.client.get("/leaderboards?offset=0&limit=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
