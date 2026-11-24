from rest_framework.routers import SimpleRouter

from .views import CategoryViewset, ProductViewSet, SellerProductViewSet

router = SimpleRouter()
router.register("categories", CategoryViewset, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("my-products", SellerProductViewSet, basename="seller-product")

urlpatterns = router.urls
