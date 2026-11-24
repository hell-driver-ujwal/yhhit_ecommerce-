from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import Product


class Cart(models.Model):
    buyer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")


    @classmethod
    def lock_for_buyer(cls, buyer):
        # Call inside an atomic block. The initial write also locks on SQLite.
        cls.objects.bulk_create([cls(buyer=buyer)], ignore_conflicts=True)
        return cls.objects.select_for_update().get(buyer=buyer)

    @staticmethod
    def tax_for(subtotal):
        return subtotal * Decimal("0.02")


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="cart_unique_product"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_positive_quantity"),
        ]

    @property
    def subtotal(self) -> int:
        return self.product.price * self.quantity
