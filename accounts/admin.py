from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm

from .models import User


class CustomUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "user_type")


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    add_form = CustomUserCreationForm

    list_display = (
        "email",
        "user_type",
        "first_name",
        "last_name",
        "phone_number",
        "is_staff",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("email",)

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "user_type",
                "first_name",
                "last_name",
                "phone_number",
                "usable_password",
                "password1",
                "password2",
            ),
        }),
    )

    fieldsets = (
        (None, {
            "fields": ("email", "password", "user_type"),
        }),
        ("Personal Information", {
            "fields": (
                "first_name",
                "last_name",
                "phone_number",
            ),
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined"),
        }),
    )
