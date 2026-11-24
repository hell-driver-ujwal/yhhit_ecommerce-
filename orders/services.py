from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User

from cart.models import Cart
from products.models import Product
from .models import Order, OrderItem


@transaction.atomic
def place_order(buyer):
    cart = Cart.lock_for_buyer(buyer)
    items = list(cart.items.select_for_update().select_related("product").order_by("product_id"))
    if not items:
        raise ValidationError({"cart": "Your cart is empty."})

    by_seller = {}
    for item in items:
        if item.product.created_by_id is None:
            raise ValidationError({"cart": f"{item.product.name} has no seller to fulfill this order."})
        by_seller.setdefault(item.product.created_by_id, []).append(item)

    orders = []
    for seller_id, seller_items in by_seller.items():
        subtotal = sum(item.subtotal for item in seller_items)
        order = Order.objects.create(buyer=buyer, seller_id=seller_id, subtotal=subtotal, tax=Cart.tax_for(subtotal))
        create_order_items(order, seller_items)
        orders.append(order)
    cart.items.all().delete()
    return orders


def create_order_items(order, items):
    lines = []
    for item in items:
        updated = Product.objects.filter(pk=item.product_id, stock__gte=item.quantity).update(
            stock=F("stock") - item.quantity
        )
        if not updated:
            raise ValidationError({"cart": f"Insufficient stock for {item.product.name}."})
        lines.append(OrderItem(
            order=order, product=item.product, product_name=item.product.name,
            unit_price=item.product.price, quantity=item.quantity,
        ))
    OrderItem.objects.bulk_create(lines)


@transaction.atomic
def change_status(order, target, actor):
    if target == Order.Status.CANCELLED:
        permitted = actor.user_type == User.UserType.BUYER and actor.pk == order.buyer_id
    else:
        permitted = actor.user_type == User.UserType.SELLER and actor.pk == order.seller_id
    if not permitted:
        raise PermissionDenied("Your account cannot make this status change.")

    allowed_from = {
        Order.Status.PROCESSING: [Order.Status.PENDING],
        Order.Status.COMPLETED: [Order.Status.PROCESSING],
        Order.Status.CANCELLED: [Order.Status.PENDING, Order.Status.PROCESSING],
    }
    changed = Order.objects.filter(pk=order.pk, status__in=allowed_from[target]).update(status=target)
    if not changed:
        raise ValidationError({"status": "This transition is unavailable from the current order status."})
    if target == Order.Status.CANCELLED:
        for item in order.items.filter(product__isnull=False).order_by("product_id"):
            Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    order.status = target
