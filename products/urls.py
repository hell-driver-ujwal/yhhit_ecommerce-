from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewset, ProductViewSet

router = DefaultRouter()
router.register("category", CategoryViewset, basename="category")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("api/", include(router.urls)),
    path("", ProductViewSet.as_view({"get": "list", "post": "create"}), name="store"),
    path("category/<slug:category_slug>", ProductViewSet.as_view({"get": "list"}), name="store"),
]
