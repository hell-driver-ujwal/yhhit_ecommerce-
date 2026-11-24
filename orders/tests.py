from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from cart.models import Cart, CartItem
from products.models import Category, Product
from .models import Order


class OrderTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.buyer = User.objects.create_user("buyer@example.com")
        cls.other = User.objects.create_user("other@example.com")
        cls.seller = User.objects.create_user("seller@example.com", user_type="seller")
        category = Category.objects.create(name="Books", slug="books")
        cls.book = Product.objects.create(category=category, created_by=cls.seller, name="Atlas", slug="atlas", stock=5, price=15)
        cls.cart = Cart.objects.create(buyer=cls.buyer)
        CartItem.objects.create(cart=cls.cart, product=cls.book, quantity=2)

    def login_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def test_checkout_and_history(self):
        self.login_as(self.buyer)
        url = reverse("orders:list")
        response = self.client.post(url, {"buyer": self.other.pk, "total": 1, "status": "completed"})
        self.assertEqual(response.status_code, 201)
        order = response.data["orders"][0]
        self.assertEqual((order["subtotal"], order["tax"], order["total"]), ("30.00", "0.60", "30.60"))
        self.assertEqual(order["status"], "pending")
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 3)
        self.assertEqual(self.cart.items.count(), 0)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(Order.objects.count(), 1)
        self.book.delete()
        detail = self.client.get(reverse("orders:detail", args=[order["id"]])).data
        self.assertEqual(detail["items"][0]["product_name"], "Atlas")
        self.assertEqual(detail["items"][0]["unit_price"], 15)
        self.assertEqual(self.client.get(url).data, [detail])

    def test_insufficient_stock_rolls_back_entire_checkout(self):
        second = Product.objects.create(category=self.book.category, created_by=self.seller, name="Pen", slug="pen", price=2, stock=0)
        CartItem.objects.create(cart=self.cart, product=second, quantity=1)
        self.login_as(self.buyer)
        self.assertEqual(self.client.post(reverse("orders:list")).status_code, 400)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)
        self.assertEqual(self.cart.items.count(), 2)
        self.assertFalse(Order.objects.exists())

    def test_access_restrictions(self):
        url = reverse("orders:list")
        self.assertEqual(self.client.post(url).status_code, 401)
        self.login_as(self.seller)
        self.assertEqual(self.client.get(url).data, [])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.login_as(self.buyer)
        pk = self.client.post(url).data["orders"][0]["id"]
        detail = reverse("orders:detail", args=[pk])
        self.assertEqual(self.client.patch(detail, {"status": "completed"}).status_code, 405)
        self.login_as(self.other)
        self.assertEqual(self.client.get(url).data, [])
        self.assertEqual(self.client.get(detail).status_code, 404)

    def test_seller_fulfillment_and_buyer_cancellation(self):
        for final in ("cancelled", "completed"):
            self.login_as(self.buyer)
            pk = self.client.post(reverse("orders:list")).data["orders"][0]["id"]
            url = reverse("orders:status", args=[pk])
            self.assertEqual(self.client.patch(url, {"status": "processing"}).status_code, 403)
            self.login_as(self.other)
            self.assertEqual(self.client.patch(url, {"status": "cancelled"}).status_code, 404)
            self.login_as(self.seller)
            self.assertEqual(self.client.patch(url, {"status": "cancelled"}).status_code, 403)
            self.assertEqual(self.client.patch(url, {"status": "completed"}).status_code, 400)
            self.assertEqual(self.client.patch(url, {"status": "processing"}).data["status"], "processing")
            if final == "cancelled":
                self.login_as(self.buyer)
            self.assertEqual(self.client.patch(url, {"status": final}).data["status"], final)
            self.login_as(self.buyer)
            self.assertEqual(self.client.patch(url, {"status": "cancelled"}).status_code, 400)
            self.book.refresh_from_db()
            self.assertEqual(self.book.stock, 5 if final == "cancelled" else 3)
            if final == "cancelled":
                CartItem.objects.create(cart=self.cart, product=self.book, quantity=2)

    def test_mixed_cart_is_split_and_seller_orders_are_private(self):
        second = User.objects.create_user("second@example.com", user_type="seller")
        pen = Product.objects.create(category=self.book.category, created_by=second, name="Pen", slug="pen", price=3, stock=2)
        CartItem.objects.create(cart=self.cart, product=pen, quantity=2)
        self.login_as(self.buyer)
        orders = self.client.post(reverse("orders:list")).data["orders"]
        self.assertEqual([o["total"] for o in orders], ["30.60", "6.12"])
        self.login_as(second)
        history = self.client.get(reverse("orders:list")).data
        self.assertEqual([o["id"] for o in history], [orders[1]["id"]])
        first = reverse("orders:status", args=[orders[0]["id"]])
        self.assertEqual(self.client.patch(first, {"status": "processing"}).status_code, 404)
        self.login_as(self.buyer)
        self.assertEqual(self.client.patch(first, {"status": "cancelled"}).status_code, 200)
        self.assertEqual(Order.objects.get(pk=orders[1]["id"]).status, "pending")
        pen.refresh_from_db()
        self.assertEqual(pen.stock, 0)
