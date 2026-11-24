from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from .models import Category, Product


class CatalogAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner@example.com", user_type="seller")
        cls.other = User.objects.create_user("other@example.com", user_type="seller")
        cls.buyer = User.objects.create_user("buyer@example.com")
        cls.admin = User.objects.create_user("staff@example.com", is_staff=True)
        cls.category = Category.objects.create(name="Books", slug="books")
        cls.product = Product.objects.create(
            name="Guide", slug="guide", price=10, stock=2, category=cls.category, created_by=cls.owner,
        )

    def login_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def test_my_products_requires_seller_and_filters_by_owner(self):
        url = reverse("seller-product-list")
        self.assertEqual(self.client.get(url).status_code, 401)
        self.login_as(self.buyer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login_as(self.owner)
        self.assertEqual([item["id"] for item in self.client.get(url).json()["data"]], [self.product.pk])
        self.login_as(self.other)
        self.assertEqual(self.client.get(url, {"created_by": self.owner.pk}).json(), {"data": []})

    def test_public_catalog(self):
        for url in (
            reverse("product-list"), reverse("product-detail", args=[self.product.pk]),
            reverse("category-list"), reverse("category-detail", args=[self.category.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_creation_requires_seller_and_sets_owner(self):
        data = {"name": "Notebook", "price": 4, "stock": 3, "category": self.category.pk, "created_by": self.other.pk}
        url = reverse("seller-product-list")
        self.assertEqual(self.client.post(url, data, format="json").status_code, 401)
        self.login_as(self.buyer)
        self.assertEqual(self.client.post(url, data, format="json").status_code, 403)
        self.login_as(self.owner)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_by"], self.owner.pk)

    def test_only_owner_can_update_or_delete(self):
        url = reverse("seller-product-detail", args=[self.product.pk])
        update = {"name": "New guide", "price": 3, "stock": 5, "category": self.category.pk}
        for user, denied in ((self.buyer, 403), (self.other, 404), (self.admin, 403)):
            self.login_as(user)
            self.assertEqual(self.client.patch(url, {"stock": 5}).status_code, denied)
            self.assertEqual(self.client.put(url, update, format="json").status_code, denied)
            self.assertEqual(self.client.delete(url).status_code, denied)
        self.login_as(self.owner)
        public = reverse("product-detail", args=[self.product.pk])
        self.assertEqual(self.client.patch(public, {"stock": 5}).status_code, 405)
        self.assertEqual(self.client.delete(public).status_code, 405)
        self.assertEqual(self.client.put(url, update, format="json").data["slug"], "new-guide")
        response = self.client.patch(url, {"stock": 7, "created_by": self.other.pk})
        self.assertEqual(response.data["stock"], 7)
        self.assertEqual(response.data["created_by"], self.owner.pk)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_categories_are_admin_managed(self):
        url = reverse("category-list")
        detail = reverse("category-detail", args=[self.category.pk])
        self.assertEqual(self.client.post(url, {"name": "Toys"}).status_code, 401)
        for user in (self.owner, self.buyer):
            self.login_as(user)
            self.assertEqual(self.client.post(url, {"name": "Toys"}).status_code, 403)
            self.assertEqual(self.client.patch(detail, {"name": "Toys"}).status_code, 403)
            self.assertEqual(self.client.delete(detail).status_code, 403)
        self.login_as(self.admin)
        self.assertEqual(self.client.patch(detail, {"description": "Books for sale"}).status_code, 200)
        self.assertEqual(self.client.delete(detail).status_code, 409)
        created = self.client.post(url, {"name": "Toys"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.delete(reverse("category-detail", args=[created.data["id"]])).status_code, 204)

    def test_search_matches_name_or_description_and_combines_with_category(self):
        stationery = Category.objects.create(name="Stationery", slug="stationery")
        notebook = Product.objects.create(
            name="Notebook", slug="notebook", description="A pocket guide to sketching",
            category=stationery, created_by=self.other, price=8, stock=5,
        )
        url = reverse("product-list")
        response = self.client.get(url, {"search": "GuIdE"})
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual([p["id"] for p in response.json()["data"]], [self.product.pk, notebook.pk])
        response = self.client.get(url, {"search": "guide", "category": "stationery"})
        self.assertEqual([p["id"] for p in response.json()["data"]], [notebook.pk])
        self.assertEqual(self.client.get(url, {"search": "absent"}).json(), {"data": []})

        self.login_as(self.owner)
        response = self.client.get(reverse("seller-product-list"), {"search": "guide"})
        self.assertEqual([p["id"] for p in response.json()["data"]], [self.product.pk])
        response = self.client.get(reverse("seller-product-list"), {"search": "notebook"})
        self.assertEqual(response.json(), {"data": []})

    def test_category_dropdown_uses_admin_defined_names(self):
        self.login_as(self.owner)
        url = reverse("seller-product-list")
        page = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertContains(page, 'value="Books"')
        schema = self.client.get(reverse("schema"), {"format": "json"}).json()
        content = schema["paths"][url]["post"]["requestBody"]["content"]
        field = content["application/x-www-form-urlencoded"]["schema"]["properties"]["category"]
        self.assertEqual(field["enum"], ["Books"])
        data = {"name": "Pocket Atlas", "stock": 2, "price": 50, "category": "Books"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["category"], self.category.pk)
        self.assertEqual(self.client.patch(reverse("seller-product-detail", args=[response.data["id"]]),
                                          {"category": "Missing"}).status_code, 400)
