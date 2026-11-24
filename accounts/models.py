from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class User(AbstractUser):
    class UserType(models.TextChoices):
        SELLER = "seller", "Seller"
        BUYER = "buyer", "Buyer"

    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True)
    user_type = models.CharField(
        max_length=6, choices=UserType.choices, default=UserType.BUYER
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user_type__in=["seller", "buyer"]),
                name="accounts_user_valid_type",
            ),
        ]

    def __str__(self):
        return self.email
