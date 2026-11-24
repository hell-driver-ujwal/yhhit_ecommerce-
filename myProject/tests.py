from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from products.models import Category


class JsonContractTests(APITestCase):
    def test_schema_and_swagger(self):
        page = self.client.get(reverse("swagger"))
        self.assertContains(page, "SwaggerUIBundle")
        schema = self.client.get(reverse("schema"), {"format": "json"})
        self.assertEqual(schema.status_code, 200)
        document = schema.json()
        self.assertIn("jwtAuth", document["components"]["securitySchemes"])
        endpoint = document["paths"]["/cart/api/items/"]["post"]
        for code, key in (("201", "data"), ("400", "ApiError")):
            shape = endpoint["responses"][code]["content"]["application/json"]["schema"]
            self.assertIn(key, str(shape))

    def test_public_success_and_auth_errors(self):
        self.assertEqual(self.client.get(reverse("product-list")).json(), {"data": []})
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json()["error"])
        response = self.client.post(reverse("accounts:logout"), [], format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json()["error"])

    def test_product_validation_and_delete_contract(self):
        seller = User.objects.create_user("seller@example.com", user_type="seller")
        self.client.force_authenticate(seller)
        category = Category.objects.create(name="Books", slug="books")
        data = {"name": "A Book", "category": category.pk, "stock": 1, "price": 4}
        url = reverse("product-list")
        created = self.client.post(url, data).json()["data"]
        for change, field in (({"name": "A-Book"}, "name"), ({"name": "!!!"}, "name"),
                              ({"name": "Two", "price": -1}, "price"), ({"name": "Two", "stock": -1}, "stock")):
            response = self.client.post(url, {**data, **change})
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json()["error"])
        deleted = self.client.delete(reverse("product-detail", args=[created["id"]]))
        self.assertEqual((deleted.status_code, deleted.content), (204, b""))
