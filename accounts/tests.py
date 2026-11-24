from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


User = get_user_model()


class UserTests(TestCase):
    def test_email_login_for_both_user_types(self):
        for user_type in User.UserType:
            with self.subTest(user_type=user_type):
                email = f"{user_type}@example.com"
                user = User.objects.create_user(email, "example-password", user_type=user_type)
                self.assertEqual(authenticate(email=email, password="example-password"), user)
                self.assertIsNone(authenticate(email=email, password="wrong-password"))

    def test_superuser_creation_without_username(self):
        user = User.objects.create_superuser("admin@example.com", "example-password")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.user_type, User.UserType.BUYER)

    def test_database_rejects_unknown_user_type(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("invalid@example.com", user_type="other")


class AccountApiTests(APITestCase):
    credentials = {"email": "seller@EXAMPLE.com", "password": " Long passphrase 84! "}

    registration = {**credentials, "confirm_password": credentials["password"]}

    def test_register_login_refresh_and_manage_own_profile(self):
        response = self.client.post(reverse("accounts:register"), {
            **self.registration, "user_type": "seller", "is_staff": True,
        })
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        self.assertNotIn("confirm_password", response.data)
        user = User.objects.get(email="seller@example.com")
        self.assertTrue(user.check_password(self.credentials["password"]))
        self.assertFalse(user.is_staff)
        self.assertEqual(user.user_type, "seller")

        login = self.client.post(reverse("accounts:login"), self.credentials)
        self.assertEqual(login.status_code, 200)
        refresh = self.client.post(reverse("accounts:token_refresh"), {"refresh": login.data["refresh"]})
        self.assertEqual(refresh.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + refresh.data["access"])
        profile = reverse("accounts:profile")
        self.assertEqual(self.client.get(profile).data, response.data)
        other = User.objects.create_user("buyer@example.com")
        update = self.client.patch(profile, {
            "id": other.pk, "first_name": "Alex", "last_name": "Rai", "phone_number": "123",
            "user_type": "buyer", "email": other.email, "is_superuser": True,
        }, format="json")
        self.assertEqual(update.status_code, 200)
        user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name, user.phone_number), ("Alex", "Rai", "123"))
        self.assertEqual(other.first_name, "")
        self.assertEqual((user.user_type, user.email, user.is_superuser), ("seller", "seller@example.com", False))

    def test_registration_validation_and_default_role(self):
        url = reverse("accounts:register")
        for changes in ({"password": "123", "confirm_password": "123"}, {"email": "invalid"}, {"user_type": "admin"}):
            self.assertEqual(self.client.post(url, {**self.registration, **changes}).status_code, 400)
        self.assertEqual(self.client.post(url, self.registration).data["user_type"], "buyer")
        self.assertEqual(self.client.post(url, self.registration).status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_requires_matching_confirmation(self):
        for fields in ({}, {"confirm_password": self.credentials["password"].strip()}):
            with self.subTest(fields=fields):
                response = self.client.post(reverse("accounts:register"), {**self.credentials, **fields})
                self.assertEqual(response.status_code, 400)
                self.assertIn("confirm_password", response.data)
                self.assertFalse(User.objects.exists())

    def test_authentication_failures(self):
        user = User.objects.create_user(**self.credentials)
        login = reverse("accounts:login")
        self.assertEqual(self.client.post(login, {**self.credentials, "password": "wrong"}).status_code, 401)
        user.is_active = False
        user.save()
        self.assertEqual(self.client.post(login, self.credentials).status_code, 401)
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 401)

    def test_logout_revokes_only_the_submitted_refresh_token(self):
        User.objects.create_user(**self.credentials)
        login = reverse("accounts:login")
        logout = reverse("accounts:logout")
        refresh = reverse("accounts:token_refresh")
        session = self.client.post(login, self.credentials).data
        other_client = APIClient()
        second_session = other_client.post(login, self.credentials).data

        self.assertEqual(APIClient().post(logout, {}).status_code, 400)
        self.assertEqual(APIClient().post(logout, {"refresh": session["access"]}).status_code, 401)
        self.assertEqual(self.client.post(logout, {}).status_code, 200)
        self.assertEqual(self.client.post(refresh, {"refresh": session["refresh"]}).status_code, 401)
        self.assertEqual(other_client.post(refresh, {"refresh": second_session["refresh"]}).status_code, 200)
        self.assertEqual(APIClient().post(logout, {"refresh": second_session["refresh"]}).status_code, 200)

    def test_guest_only_endpoints_require_logout(self):
        User.objects.create_user(**self.credentials)
        login = reverse("accounts:login")
        register = reverse("accounts:register")
        new_account = {**self.registration, "email": "new@example.com"}
        access = self.client.post(login, self.credentials).data["access"]
        bearer_client = APIClient()
        bearer_client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
        for client in (self.client, bearer_client):
            self.assertEqual(client.post(register, new_account).status_code, 403)
            self.assertEqual(client.post(login, self.credentials).status_code, 403)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.client.post(reverse("accounts:logout")).status_code, 200)
        self.assertEqual(self.client.post(register, new_account).status_code, 201)
        self.assertEqual(self.client.post(login, self.credentials).status_code, 200)

    def test_browser_login_and_logout_apply_csrf_checks(self):
        User.objects.create_user(**self.credentials)
        client = APIClient(enforce_csrf_checks=True)
        login = reverse("accounts:login")
        origin = {"HTTP_ORIGIN": "http://testserver"}
        client.options(login)
        self.assertEqual(client.post(login, self.credentials, **origin).status_code, 403)
        headers = {**origin, "HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}
        self.assertEqual(client.post(login, self.credentials, **headers).status_code, 200)
        logout = reverse("accounts:logout")
        self.assertEqual(client.post(logout, **origin).status_code, 403)
        page = client.get(logout, HTTP_ACCEPT="text/html")
        self.assertNotIn(b'name="refresh"', page.content)
        form = {"refresh": "", "csrfmiddlewaretoken": client.cookies["csrftoken"].value}
        result = client.post(logout, form, HTTP_ACCEPT="text/html", **origin)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(client.post(login, self.credentials, **headers).status_code, 200)
