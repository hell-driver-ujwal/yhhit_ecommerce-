from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializers, ProductSerializers


class IsSeller(BasePermission):
    message = "A seller account is required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == User.UserType.SELLER


class CategoryPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


@extend_schema(tags=["Catalog"])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializers
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter


@extend_schema(tags=["My products"])
@extend_schema_view(list=extend_schema(summary="List my products"))
class SellerProductViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                           mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializers
    authentication_classes = (JWTAuthentication, SessionAuthentication)
    permission_classes = (IsSeller,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        return super().get_queryset().filter(created_by=self.request.user).order_by("pk")

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset) if self.action == "list" else queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema(tags=["Categories"])
class CategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.prefetch_related("products")
    serializer_class = CategorySerializers
    authentication_classes = (JWTAuthentication, SessionAuthentication)
    permission_classes = (CategoryPermission,)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This category still contains products."},
                status=status.HTTP_409_CONFLICT,
            )
