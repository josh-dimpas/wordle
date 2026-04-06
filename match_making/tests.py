from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from game.models import Game
from users.models import Account
from .models import Lobby, LobbyMembership, Match, MatchPlayer, MatchGame


class LobbyCreateViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_create_lobby_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/matchmaking/lobby/create")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_lobby_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post("/matchmaking/lobby/create")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("code", response.data)
        self.assertIn("owner", response.data)
        self.assertEqual(response.data["owner"], "testuser")

    def test_create_lobby_generates_unique_code(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response1 = self.client.post("/matchmaking/lobby/create")
        response2 = self.client.post("/matchmaking/lobby/create")

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response1.data["code"], response2.data["code"])

    def test_create_lobby_player_added_to_lobby(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post("/matchmaking/lobby/create")

        lobby = Lobby.objects.get(code=response.data["code"])
        self.assertTrue(lobby.players.filter(id=self.user.id).exists())

    def test_create_lobby_removes_from_existing_lobby(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response1 = self.client.post("/matchmaking/lobby/create")
        code1 = response1.data["code"]

        response2 = self.client.post("/matchmaking/lobby/create")
        code2 = response2.data["code"]

        self.assertNotEqual(code1, code2)
        self.assertFalse(Lobby.objects.filter(code=code1).exists())


class LobbyJoinViewTests(APITestCase):
    def setUp(self):
        self.user1 = Account.objects.create_user(
            username="join1", password="testpass123"
        )
        self.user2 = Account.objects.create_user(
            username="join2", password="testpass123"
        )
        refresh1 = RefreshToken.for_user(self.user1)
        refresh2 = RefreshToken.for_user(self.user2)
        self.token1 = str(refresh1.access_token)
        self.token2 = str(refresh2.access_token)

    def _create_lobby(self, owner, code, has_started=False):
        lobby = Lobby.objects.create(owner=owner, code=code, has_started=has_started)
        LobbyMembership.objects.create(lobby=lobby, player=owner)
        return lobby

    def test_join_lobby_requires_authentication(self):
        lobby = self._create_lobby(self.user1, "jnjoin1")
        self.client.credentials()
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": lobby.code}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_join_lobby_success(self):
        lobby = self._create_lobby(self.user1, "jnjoin2")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": lobby.code}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], lobby.code)
        self.assertEqual(len(response.data["players"]), 2)

    def test_join_lobby_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": "nonexist"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    def test_join_lobby_already_started(self):
        lobby = self._create_lobby(self.user1, "jnjoin3", has_started=True)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": lobby.code}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_join_lobby_removes_from_existing_lobby(self):
        lobby2 = self._create_lobby(self.user2, "jnjoin4")
        lobby1 = self._create_lobby(self.user1, "jnjoin5")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": lobby1.code}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Lobby.objects.filter(code=lobby2.code).exists())

    def test_join_lobby_already_member(self):
        lobby = self._create_lobby(self.user1, "jnjoin6")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            "/matchmaking/lobby/join", {"code": lobby.code}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


class LobbyLeaveViewTests(APITestCase):
    def setUp(self):
        self.user1 = Account.objects.create_user(
            username="leave1", password="testpass123"
        )
        self.user2 = Account.objects.create_user(
            username="leave2", password="testpass123"
        )
        self.lobby = Lobby.objects.create(owner=self.user1, code="lvleave1")
        LobbyMembership.objects.create(lobby=self.lobby, player=self.user1)
        LobbyMembership.objects.create(lobby=self.lobby, player=self.user2)

        refresh1 = RefreshToken.for_user(self.user1)
        refresh2 = RefreshToken.for_user(self.user2)
        self.token1 = str(refresh1.access_token)
        self.token2 = str(refresh2.access_token)

    def test_leave_lobby_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/matchmaking/lobby/leave")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_leave_lobby_not_in_lobby(self):
        other_user = Account.objects.create_user(
            username="leave_other", password="testpass123"
        )
        refresh = RefreshToken.for_user(other_user)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post("/matchmaking/lobby/leave")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_leave_lobby_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post("/matchmaking/lobby/leave")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertFalse(self.lobby.players.filter(id=self.user2.id).exists())

    def test_leave_lobby_lobby_deleted_when_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        self.client.post("/matchmaking/lobby/leave")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/leave")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Lobby.objects.filter(code=self.lobby.code).exists())

    def test_leave_lobby_new_owner_assigned(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/leave")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lobby.refresh_from_db()
        self.assertEqual(self.lobby.owner, self.user2)


class LobbyCurrentViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="curr1", password="testpass123"
        )
        self.lobby = Lobby.objects.create(owner=self.user, code="cucurr1")
        LobbyMembership.objects.create(lobby=self.lobby, player=self.user)

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_current_lobby_requires_authentication(self):
        self.client.credentials()
        response = self.client.get("/matchmaking/lobby/current")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_lobby_returns_lobby_info(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get("/matchmaking/lobby/current")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], self.lobby.code)
        self.assertEqual(response.data["owner"], "curr1")
        self.assertTrue(response.data["is_owner"])

    def test_current_lobby_returns_message_when_not_in_lobby(self):
        other_user = Account.objects.create_user(
            username="curr_other", password="testpass123"
        )
        refresh = RefreshToken.for_user(other_user)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/matchmaking/lobby/current")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)


class LobbyReadyViewTests(APITestCase):
    def setUp(self):
        self.user1 = Account.objects.create_user(
            username="ready1", password="testpass123"
        )
        self.user2 = Account.objects.create_user(
            username="ready2", password="testpass123"
        )
        self.lobby = Lobby.objects.create(owner=self.user1, code="rdready1")
        LobbyMembership.objects.create(lobby=self.lobby, player=self.user1)
        LobbyMembership.objects.create(lobby=self.lobby, player=self.user2)

        refresh1 = RefreshToken.for_user(self.user1)
        refresh2 = RefreshToken.for_user(self.user2)
        self.token1 = str(refresh1.access_token)
        self.token2 = str(refresh2.access_token)

    def test_ready_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/matchmaking/lobby/ready")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ready_not_in_lobby(self):
        other_user = Account.objects.create_user(
            username="ready_other", password="testpass123"
        )
        refresh = RefreshToken.for_user(other_user)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post("/matchmaking/lobby/ready")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ready_lobby_already_started(self):
        self.lobby.has_started = True
        self.lobby.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/ready")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_ready_toggles_ready_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")

        response1 = self.client.post("/matchmaking/lobby/ready")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        membership = LobbyMembership.objects.get(lobby=self.lobby, player=self.user1)
        self.assertTrue(membership.is_ready)

        response2 = self.client.post("/matchmaking/lobby/ready")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        membership.refresh_from_db()
        self.assertFalse(membership.is_ready)


class LobbyStartViewTests(APITestCase):
    def setUp(self):
        self.user1 = Account.objects.create_user(
            username="start1", password="testpass123"
        )
        self.user2 = Account.objects.create_user(
            username="start2", password="testpass123"
        )
        self.lobby = Lobby.objects.create(owner=self.user1, code="ststart1")
        LobbyMembership.objects.create(
            lobby=self.lobby, player=self.user1, is_ready=True
        )
        LobbyMembership.objects.create(
            lobby=self.lobby, player=self.user2, is_ready=True
        )

        refresh1 = RefreshToken.for_user(self.user1)
        refresh2 = RefreshToken.for_user(self.user2)
        self.token1 = str(refresh1.access_token)
        self.token2 = str(refresh2.access_token)

    def test_start_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/matchmaking/lobby/start")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_start_not_in_lobby(self):
        other_user = Account.objects.create_user(
            username="start_other", password="testpass123"
        )
        refresh = RefreshToken.for_user(other_user)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_not_owner(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_start_lobby_already_started(self):
        self.lobby.has_started = True
        self.lobby.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_start_not_all_ready(self):
        membership = LobbyMembership.objects.get(lobby=self.lobby, player=self.user2)
        membership.is_ready = False
        membership.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_start_less_than_two_players(self):
        LobbyMembership.objects.filter(lobby=self.lobby, player=self.user2).delete()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_start_success_creates_match(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post("/matchmaking/lobby/start")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["status"], "active")

        self.lobby.refresh_from_db()
        self.assertTrue(self.lobby.has_started)

        match = Match.objects.get(id=response.data["id"])
        self.assertEqual(match.status, "active")
        self.assertEqual(match.players.count(), 2)

    def test_start_success_resets_ready_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        self.client.post("/matchmaking/lobby/start")

        for membership in LobbyMembership.objects.filter(lobby=self.lobby):
            membership.refresh_from_db()
            self.assertFalse(membership.is_ready)


def create_test_match():
    user1 = Account.objects.create_user(username="mp1", password="test")
    user2 = Account.objects.create_user(username="mp2", password="test")

    lobby = Lobby.objects.create(owner=user1, code="testmatch1")
    LobbyMembership.objects.create(lobby=lobby, player=user1, is_ready=True)
    LobbyMembership.objects.create(lobby=lobby, player=user2, is_ready=True)

    refresh1 = RefreshToken.for_user(user1)
    refresh2 = RefreshToken.for_user(user2)

    return user1, user2, lobby, str(refresh1.access_token), str(refresh2.access_token)


def start_match_via_api(client, token):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client.post("/matchmaking/lobby/start")


class MatchStateViewTests(APITestCase):
    def setUp(self):
        self.user1, self.user2, self.lobby, self.token1, self.token2 = (
            create_test_match()
        )
        response = start_match_via_api(self.client, self.token1)
        self.match_id = response.data["id"]

    def test_match_state_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(f"/matchmaking/match/{self.match_id}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_match_state_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.get("/matchmaking/match/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_match_state_user_not_in_match(self):
        other_user = Account.objects.create_user(username="notinmatch", password="test")
        refresh = RefreshToken.for_user(other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = self.client.get(f"/matchmaking/match/{self.match_id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_match_state_returns_match_info(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.get(f"/matchmaking/match/{self.match_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["status"], "active")

    def test_match_state_includes_players_with_lives(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.get(f"/matchmaking/match/{self.match_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("players", response.data)
        self.assertEqual(len(response.data["players"]), 2)

    def test_match_state_includes_current_word_index(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.get(f"/matchmaking/match/{self.match_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for player in response.data["players"]:
            self.assertIn("current_word_index", player)
            self.assertIn("lives", player)


class MatchGuessViewTests(APITestCase):
    def setUp(self):
        self.user1, self.user2, self.lobby, self.token1, self.token2 = (
            create_test_match()
        )
        response = start_match_via_api(self.client, self.token1)
        self.match_id = response.data["id"]

        self.match = Match.objects.get(id=self.match_id)
        self.match_player1 = MatchPlayer.objects.get(
            match=self.match, player=self.user1
        )
        self.match_player2 = MatchPlayer.objects.get(
            match=self.match, player=self.user2
        )

        self.active_game = MatchGame.objects.get(
            match=self.match, player=self.user1, is_active=True
        )
        self.game = Game.objects.get(id=self.active_game.game_id)
        self.correct_word = self.game.word

    def test_guess_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guess_match_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            "/matchmaking/match/99999/guess",
            {"input": self.correct_word},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guess_match_not_active(self):
        self.match.status = "completed"
        self.match.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guess_user_not_in_match(self):
        other_user = Account.objects.create_user(username="notinmatch", password="test")
        refresh = RefreshToken.for_user(other_user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guess_wrong_word_length(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess", {"input": "ab"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_guess_correct_word_returns_success_message(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("Correct", response.data["message"])

    def test_guess_wrong_word_returns_game_state(self):
        word_length = len(self.correct_word)
        wrong_word = (
            "a" * word_length
            if self.correct_word != "a" * word_length
            else "b" * word_length
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        response = self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": wrong_word},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tries", response.data)

    def test_guess_correct_word_deducts_opponent_life(self):
        initial_lives = self.match_player2.lives

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )

        self.match_player2.refresh_from_db()
        self.assertEqual(self.match_player2.lives, initial_lives - 1)

    def test_guess_correct_word_opponent_no_lives_sets_winner(self):
        self.match_player2.lives = 1
        self.match_player2.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )

        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "completed")
        self.assertEqual(self.match.winner, self.user1)

    def test_guess_sets_next_game_active(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )

        self.active_game.refresh_from_db()
        self.assertFalse(self.active_game.is_active)

        next_game = MatchGame.objects.filter(
            match=self.match, player=self.user1, word_index=1
        ).first()
        self.assertTrue(next_game.is_active)

    def test_guess_updates_match_player_word_index(self):
        initial_index = self.match_player1.current_word_index

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        self.client.post(
            f"/matchmaking/match/{self.match_id}/guess",
            {"input": self.correct_word},
            format="json",
        )

        self.match_player1.refresh_from_db()
        self.assertEqual(self.match_player1.current_word_index, initial_index + 1)
