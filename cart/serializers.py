from rest_framework import serializers

from .models import CartItem


class AddItemSerializer(serializers.Serializer):
    product = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="product.name")
    price = serializers.IntegerField(source="product.price")

    class Meta:
        model = CartItem
        fields = ("id", "product", "name", "price", "quantity", "subtotal")


class CartSummarySerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    quantity = serializers.IntegerField()
    total = serializers.IntegerField()
    tax = serializers.DecimalField(max_digits=24, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=24, decimal_places=2)
