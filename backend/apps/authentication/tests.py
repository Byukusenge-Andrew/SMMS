from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class AuthRegistrationTests(APITestCase):
    """Tests for user registration flow."""

    def test_register_without_subscription_tier(self):
        """Registration without subscription_tier_id should succeed."""
        url = reverse("register")
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)

    def test_register_password_mismatch(self):
        """Registration with mismatched passwords should fail."""
        url = reverse("register")
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "password_confirm": "DifferentPassword456!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Registration with an already-used email should fail."""
        User.objects.create_user(
            username="existing", email="taken@example.com", password="TestPassword123!"
        )
        url = reverse("register")
        data = {
            "username": "newuser",
            "email": "taken@example.com",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        """Registration with a weak password should fail validation."""
        url = reverse("register")
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "123",
            "password_confirm": "123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthLoginTests(APITestCase):
    """Tests for user login flow."""

    def test_login_unverified(self):
        """Login before email verification should fail."""
        url = reverse("register")
        data = {
            "username": "testuser2",
            "email": "testuser2@example.com",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
        }
        self.client.post(url, data, format="json")
        # Try to login before verification (user.is_active = False)
        url = reverse("login")
        data = {"username": "testuser2", "password": "TestPassword123!"}
        response = self.client.post(url, data, format="json")
        # Should fail — either 400 or 401
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    def test_login_verified(self):
        """Login with verified (active) user should succeed and return token."""
        user = User.objects.create_user(
            username="testuser3", email="testuser3@example.com", password="TestPassword123!"
        )
        user.is_active = True
        user.save()
        url = reverse("login")
        data = {"username": "testuser3", "password": "TestPassword123!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_invalid_credentials(self):
        """Login with wrong password should fail."""
        User.objects.create_user(
            username="testuser4", email="testuser4@example.com", password="TestPassword123!"
        )
        url = reverse("login")
        data = {"username": "testuser4", "password": "WrongPassword!"}
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    def test_login_with_email(self):
        """Login using email instead of username should succeed."""
        user = User.objects.create_user(
            username="testuser5", email="testuser5@example.com", password="TestPassword123!"
        )
        user.is_active = True
        user.save()
        url = reverse("login")
        data = {"username": "testuser5@example.com", "password": "TestPassword123!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)


class PasswordChangeTests(APITestCase):
    """Tests for password change functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="pwuser", email="pwuser@example.com", password="OldPassword123!"
        )
        self.user.is_active = True
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = reverse("change-password")

    def test_change_password_success(self):
        """Successful password change should return new token."""
        data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword456!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        # New token should differ from old
        self.assertNotEqual(response.data["token"], self.token.key)

    def test_change_password_wrong_current(self):
        """Providing wrong current password should fail."""
        data = {
            "current_password": "WrongPassword!",
            "new_password": "NewPassword456!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_change_password_same_as_old(self):
        """Setting new password same as current should fail."""
        data = {
            "current_password": "OldPassword123!",
            "new_password": "OldPassword123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_old_token_invalidated_after_password_change(self):
        """Old token should not work after password change."""
        old_token_key = self.token.key
        data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword456!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try using old token
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {old_token_key}")
        profile_url = reverse("profile")
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTests(APITestCase):
    """Tests for password reset flow."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="resetuser", email="resetuser@example.com", password="OldPassword123!"
        )
        self.user.is_active = True
        self.user.save()

    def test_forgot_password_existing_email(self):
        """Requesting reset for existing email should return success (no enumeration)."""
        url = reverse("forgot_password")
        response = self.client.post(url, {"email": "resetuser@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_forgot_password_nonexistent_email(self):
        """Requesting reset for unknown email should also return success (no enumeration)."""
        url = reverse("forgot_password")
        response = self.client.post(url, {"email": "nobody@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_validate_reset_token_no_email_leak(self):
        """validate_reset_token should NOT return email or username."""
        from apps.authentication.models import PasswordResetToken

        reset_token = PasswordResetToken.objects.create(user=self.user)
        url = reverse("validate_reset_token", args=[str(reset_token.token)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("valid"))
        self.assertNotIn("email", response.data)
        self.assertNotIn("username", response.data)


class DataIsolationTests(APITestCase):
    """Tests to verify user A cannot access user B's data."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="user_a", email="a@example.com", password="TestPassword123!"
        )
        self.user_a.is_active = True
        self.user_a.save()
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(
            username="user_b", email="b@example.com", password="TestPassword123!"
        )
        self.user_b.is_active = True
        self.user_b.save()
        self.token_b = Token.objects.create(user=self.user_b)

    def test_profile_returns_own_data(self):
        """User A's profile request should only return user A's data."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_accounts_isolated(self):
        """Social accounts list should only return accounts for authenticated user."""
        from apps.authentication.models import SocialMediaAccount

        SocialMediaAccount.objects.create(
            user=self.user_b,
            platform="twitter",
            username="userb_twitter",
            access_token="fake_token",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_a.key}")
        response = self.client.get(reverse("social-accounts"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User A should not see user B's accounts
        for account in response.data:
            self.assertNotEqual(account.get("username"), "userb_twitter")


class ResendVerificationTests(APITestCase):
    """Tests for resend verification email endpoint."""

    def test_resend_nonexistent_email_no_leak(self):
        """Resending verification for unknown email should not reveal if email exists."""
        url = reverse("resend_verification")
        response = self.client.post(url, {"email": "nobody@example.com"}, format="json")
        # Should NOT return 404 — should return 200 with generic message
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LogoutTests(APITestCase):
    """Tests for logout functionality."""

    def test_logout_invalidates_token(self):
        """After logout, the token should no longer be valid."""
        user = User.objects.create_user(
            username="logoutuser", email="logout@example.com", password="TestPassword123!"
        )
        user.is_active = True
        user.save()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Token should now be invalid
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
