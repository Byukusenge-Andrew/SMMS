from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_register(self):
        url = reverse("register")
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "TestPassword123",
            "password_confirm": "TestPassword123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)

    def test_login_unverified(self):
        # Register user
        url = reverse("register")
        data = {
            "username": "testuser2",
            "email": "testuser2@example.com",
            "password": "TestPassword123",
            "password_confirm": "TestPassword123",
        }
        self.client.post(url, data, format="json")
        # Try to login before verification
        url = reverse("login")
        data = {"username": "testuser2", "password": "TestPassword123"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_login_verified(self):
        # Register and manually activate user
        user = User.objects.create_user(username="testuser3", email="testuser3@example.com", password="TestPassword123")
        user.is_active = True
        user.save()
        url = reverse("login")
        data = {"username": "testuser3", "password": "TestPassword123"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)
