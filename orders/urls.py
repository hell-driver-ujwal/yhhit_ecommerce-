from django.urls import path

from .views import OrderViewSet

app_name = "orders"

urlpatterns = [
    path("", OrderViewSet.as_view({"get": "list", "post": "create"}), name="list"),
    path("<int:pk>/status/", OrderViewSet.as_view({"patch": "update_status"}), name="status"),
    path("<int:pk>/", OrderViewSet.as_view({"get": "retrieve"}), name="detail"),
]
