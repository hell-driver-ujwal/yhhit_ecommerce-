from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ("product", "product_name", "unit_price", "quantity")
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "seller", "status", "total", "created_at")
    list_filter = ("status",)
    readonly_fields = ("buyer", "seller", "created_at", "status", "subtotal", "tax", "total")
    inlines = (OrderItemInline,)
    actions = None

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
