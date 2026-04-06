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


