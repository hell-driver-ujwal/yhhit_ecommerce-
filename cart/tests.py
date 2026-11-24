from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from products.models import Category, Product
from .models import Cart, CartItem


class CartApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.buyer = User.objects.create_user("buyer@example.com")
        cls.other = User.objects.create_user("other@example.com")
        cls.seller = User.objects.create_user("seller@example.com", user_type="seller")
        category = Category.objects.create(name="Books", slug="books")
        cls.product = Product.objects.create(name="Atlas", slug="atlas", category=category, price=15, stock=3)

    def login_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def add(self, **fields):
        return self.client.post(reverse("cart:add"), {"product": self.product.pk, **fields}, format="json")

    def test_only_authenticated_buyers_can_use_cart_endpoints(self):
        for user, denied in ((None, 401), (self.seller, 403)):
            if user:
                self.login_as(user)
            self.assertEqual(self.client.get(reverse("cart:detail")).status_code, denied)
            self.assertEqual(self.add().status_code, denied)
            self.assertEqual(self.client.post(reverse("cart:decrease", args=[1])).status_code, denied)
            self.assertEqual(self.client.delete(reverse("cart:delete", args=[1])).status_code, denied)
        self.assertFalse(Cart.objects.exists())

    def test_add_total_decrease_and_remove(self):
        self.login_as(self.buyer)
        self.assertEqual(self.client.get(reverse("cart:detail")).data["items"], [])
        item = self.add()
        self.assertEqual(item.status_code, 201)
        self.assertEqual(self.add(quantity=2).status_code, 200)
        cart = self.client.get(reverse("cart:detail")).data
        self.assertEqual(len(cart["items"]), 1)
        self.assertEqual(cart["items"][0]["subtotal"], 45)
        self.assertEqual((cart["quantity"], cart["total"], cart["tax"], cart["grand_total"]), (3, 45, "0.90", "45.90"))
        pk = item.data["id"]
        for remaining in (2, 1):
            self.assertEqual(self.client.post(reverse("cart:decrease", args=[pk])).data["quantity"], remaining)
        self.assertEqual(self.client.post(reverse("cart:decrease", args=[pk])).status_code, 204)
        pk = self.add(quantity=3).data["id"]
        self.assertEqual(self.client.delete(reverse("cart:delete", args=[pk])).status_code, 204)
        self.assertFalse(CartItem.objects.exists())

    def test_stock_checks_preserve_existing_quantity(self):
        self.login_as(self.buyer)
        for quantity in (0, -1, 4):
            self.assertEqual(self.add(quantity=quantity).status_code, 400)
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(self.add(quantity=2).status_code, 201)
        self.assertEqual(self.add(quantity=2).status_code, 400)
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_buyers_cannot_access_another_cart(self):
        self.login_as(self.buyer)
        pk = self.add().data["id"]
        self.login_as(self.other)
        self.assertEqual(self.client.get(reverse("cart:detail")).data["items"], [])
        self.assertEqual(self.client.post(reverse("cart:decrease", args=[pk])).status_code, 404)
        self.assertEqual(self.client.delete(reverse("cart:delete", args=[pk])).status_code, 404)
        self.assertEqual(self.add(buyer=self.buyer.pk).status_code, 201)
        self.assertEqual(Cart.objects.count(), 2)
        self.assertEqual(CartItem.objects.get(pk=pk).quantity, 1)
