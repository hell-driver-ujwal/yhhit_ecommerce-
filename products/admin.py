from django.contrib import admin

from accounts.models import User
from .models import Category, Product

admin.site.register(Category)

class ProductAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return super().has_add_permission(request) and request.user.user_type == User.UserType.SELLER

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or obj.created_by_id == request.user.pk)

    def has_delete_permission(self, request, obj=None):
        # Disable bulk deletion, which skips per-object permission checks.
        return obj is not None and obj.created_by_id == request.user.pk and super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Product,ProductAdmin)