from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from cart.views import IsBuyer
from .models import Order
from .serializers import OrderSerializer, StatusSerializer
from .services import change_status, place_order


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    authentication_classes = (JWTAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        if self.action == "update_status":
            return StatusSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == "create":
            return [IsBuyer()]
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        user = self.request.user
        orders = Order.objects.filter(seller=user) if user.user_type == User.UserType.SELLER else Order.objects.filter(buyer=user)
        return orders.prefetch_related("items").order_by("-created_at", "-pk")

    @extend_schema(
        request=None, description="Check out the buyer’s cart. Each seller receives a separate order.",
        responses={201: inline_serializer("CheckoutResult", fields={"orders": OrderSerializer(many=True)})},
    )
    def create(self, request):
        orders = place_order(request.user)
        return Response({"orders": self.get_serializer(orders, many=True).data}, status=status.HTTP_201_CREATED)

    @extend_schema(responses=OrderSerializer, description="Sellers move their pending orders to processing, then completed. Buyers can cancel their pending or processing orders.")
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_status(order, serializer.validated_data["status"], request.user)
        return Response(OrderSerializer(order).data)
