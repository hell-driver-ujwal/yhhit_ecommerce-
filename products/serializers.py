from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, Product


class AutoSlugMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "name" in attrs:
            slug = slugify(attrs["name"])
            if not slug:
                raise serializers.ValidationError({"name": "The name must produce a nonempty URL slug."})
            matches = self.Meta.model.objects.filter(slug=slug)
            if self.instance:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise serializers.ValidationError({"name": "This name produces an existing URL slug."})
            attrs["slug"] = slug
        return attrs

    def save(self, **kwargs):
        try:
            with transaction.atomic():
                return super().save(**kwargs)
        except IntegrityError:
            if "name" in self.validated_data:
                matches = self.Meta.model.objects.filter(
                    Q(name=self.validated_data["name"]) | Q(slug=self.validated_data["slug"])
                )
                if self.instance:
                    matches = matches.exclude(pk=self.instance.pk)
                if matches.exists():
                    raise serializers.ValidationError({"name": "This name or URL slug is already in use."})
            raise


class ProductSerializers(AutoSlugMixin, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("slug", "created_by")
        extra_kwargs = {"price": {"min_value": 0}, "stock": {"min_value": 0}}


class CategorySerializers(AutoSlugMixin, serializers.ModelSerializer):
    products = ProductSerializers(many=True, read_only=True)

    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("slug",)
