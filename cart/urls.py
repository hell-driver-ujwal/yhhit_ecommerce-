from django.urls import path

from .views import AddItemView, CartView, DeleteItemView, ReduceItemView

app_name = "cart"

urlpatterns = [
    path("", CartView.as_view(), name="detail"),
    path("items/", AddItemView.as_view(), name="add"),
    path("items/<int:pk>/decrease/", ReduceItemView.as_view(), name="decrease"),
    path("items/<int:pk>/", DeleteItemView.as_view(), name="delete"),
]
