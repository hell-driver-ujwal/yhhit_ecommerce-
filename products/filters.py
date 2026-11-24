from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Product


class ProductFilter(filters.FilterSet):
    search = filters.CharFilter(method="search_catalog", label="Search product names and descriptions")
    category = filters.CharFilter(field_name="category__slug", label="Category slug")

    class Meta:
        model = Product
        fields = ("search", "category")

    def search_catalog(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))
