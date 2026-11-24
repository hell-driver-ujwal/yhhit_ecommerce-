from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializers, ProductSerializers


class ProductPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        return request.method != "POST" or request.user.user_type == User.UserType.SELLER

    def has_object_permission(self, request, view, product):
        return request.method in SAFE_METHODS or product.created_by_id == request.user.pk


class IsSeller(BasePermission):
    message = "A seller account is required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == User.UserType.SELLER


class CategoryPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializers
    authentication_classes = (JWTAuthentication, SessionAuthentication)
    permission_classes = (ProductPermission,)

    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter

    def filter_queryset(self, queryset):
        if self.action in ("list", "my_products"):
            return super().filter_queryset(queryset)
        return queryset

    def get_queryset(self):
        products = super().get_queryset()
        if "category_slug" in self.kwargs:
            category = get_object_or_404(Category, slug=self.kwargs["category_slug"])
            return products.filter(category=category)
        return products

    @extend_schema(
        operation_id="seller_my_products", summary="My products",
        description="List products created by the signed-in seller.",
        responses=ProductSerializers(many=True),
    )
    @action(detail=False, methods=["get"], url_path="my-products", permission_classes=[IsSeller])
    def my_products(self, request):
        products = self.filter_queryset(self.get_queryset().filter(created_by=request.user)).order_by("pk")
        return Response(self.get_serializer(products, many=True).data)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


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
