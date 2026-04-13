from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Account


class AccountModelTests(TestCase):
    def test_account_creation(self):
        user = Account.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))

    def test_account_default_values(self):
        user = Account.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(user.wins, 0)
        self.assertEqual(user.matches_count, 0)

    def test_account_str(self):
        user = Account.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(str(user), "testuser")

    def test_account_increment_wins(self):
        user = Account.objects.create_user(username="testuser", password="testpass123")
        user.wins = 5
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.wins, 5)

    def test_account_increment_matches_count(self):
        user = Account.objects.create_user(username="testuser", password="testpass123")
        user.matches_count = 10
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.matches_count, 10)


class RegisterViewTests(APITestCase):
    def test_register_success(self):
        response = self.client.post(
            "/register",
            {"username": "newuser", "password": "testpass123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.json())
        self.assertTrue(Account.objects.filter(username="newuser").exists())

    def test_register_duplicate_username(self):
        Account.objects.create_user(username="existinguser", password="testpass123")

        response = self.client.post(
            "/register",
            {"username": "existinguser", "password": "testpass123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", response.json())

    def test_register_invalid_json(self):
        response = self.client.post(
            "/register", "not valid json", content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.json())


class LoginViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_login_success(self):
        response = self.client.post(
            "/login", {"username": "testuser", "password": "testpass123"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):
        response = self.client.post(
            "/login", {"username": "testuser", "password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            "/login", {"username": "nonexistent", "password": "testpass123"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_username(self):
        response = self.client.post("/login", {"password": "testpass123"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        response = self.client.post("/login", {"username": "testuser"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshTokenViewTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.refresh_token = str(refresh)

    def test_refresh_token_success(self):
        response = self.client.post("/refresh-token", {"refresh": self.refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_token_invalid(self):
        response = self.client.post("/refresh-token", {"refresh": "invalid_token"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_missing(self):
        response = self.client.post("/refresh-token", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class JWTAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username="testuser", password="testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_access_token_authentication(self):
        response = self.client.post(
            "/play", HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_access_token_missing(self):
        response = self.client.post("/play")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_invalid(self):
        response = self.client.post("/play", HTTP_AUTHORIZATION="Bearer invalid_token")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_malformed(self):
        response = self.client.post("/play", HTTP_AUTHORIZATION="invalid_format")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
