from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


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
