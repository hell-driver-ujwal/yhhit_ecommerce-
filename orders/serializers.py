from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("product", "product_name", "unit_price", "quantity")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=24, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "seller", "status", "created_at", "items", "subtotal", "tax", "total")
        read_only_fields = fields


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        Order.Status.PROCESSING, Order.Status.COMPLETED, Order.Status.CANCELLED,
    ])
