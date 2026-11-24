from drf_spectacular.utils import extend_schema
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from products.models import Product
from .models import Cart, CartItem
from .serializers import AddItemSerializer, CartItemSerializer, CartSummarySerializer


class IsBuyer(BasePermission):
    message = "A buyer account is required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == User.UserType.BUYER


class BuyerCartView(APIView):
    authentication_classes = (JWTAuthentication, SessionAuthentication)
    permission_classes = (IsBuyer,)

@extend_schema(responses=CartSummarySerializer, description="Retrieve the signed-in buyer’s cart and totals.")
class CartView(BuyerCartView):
    def get(self, request):
        items = list(CartItem.objects.filter(cart__buyer=request.user).select_related("product").order_by("pk"))
        total = sum(item.subtotal for item in items)
        tax = Cart.tax_for(total)
        return Response({
            "items": CartItemSerializer(items, many=True).data,
            "quantity": sum(item.quantity for item in items),
            "total": total,
            "tax": format(tax, ".2f"),
            "grand_total": format(total + tax, ".2f"),
        })


@extend_schema(request=AddItemSerializer, responses={200: CartItemSerializer, 201: CartItemSerializer}, description="Add to the buyer’s cart within available stock. Repeated additions increase the quantity.")
class AddItemView(BuyerCartView):
    @transaction.atomic
    def post(self, request):
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart.lock_for_buyer(request.user)
        product = get_object_or_404(Product.objects.select_for_update(), pk=serializer.validated_data["product"])
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        quantity = serializer.validated_data["quantity"]
        if not created:
            quantity += item.quantity
        if quantity > product.stock:
            raise ValidationError({"quantity": "The requested quantity exceeds available stock."})
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(request=None, responses={200: CartItemSerializer, 204: None}, description="Decrease one unit. The last unit removes the item.")
class ReduceItemView(BuyerCartView):
    @transaction.atomic
    def post(self, request, pk):
        item = get_object_or_404(CartItem.objects.select_related("product"), cart=Cart.lock_for_buyer(request.user), pk=pk)
        if item.quantity == 1:
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        item.quantity -= 1
        item.save(update_fields=["quantity"])
        return Response(CartItemSerializer(item).data)


@extend_schema(responses={204: None}, description="Remove the entire item from the current buyer’s cart.")
class DeleteItemView(BuyerCartView):
    @transaction.atomic
    def delete(self, request, pk):
        item = get_object_or_404(CartItem, cart=Cart.lock_for_buyer(request.user), pk=pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
