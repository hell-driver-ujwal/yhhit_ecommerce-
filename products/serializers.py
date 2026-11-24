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


class ProductCategoryField(serializers.PrimaryKeyRelatedField):
    """HTML forms display category names. JSON clients use the primary key."""

    def get_choices(self, cutoff=None):
        names = self.get_queryset().values_list("name", flat=True)[:cutoff]
        return {name: name for name in names}

    def to_internal_value(self, data):
        request = self.context.get("request")
        if request and request.content_type.split(";")[0] in ("application/x-www-form-urlencoded", "multipart/form-data"):
            try:
                return self.get_queryset().get(name=data)
            except Category.DoesNotExist:
                raise serializers.ValidationError("Select an existing category.")
        return super().to_internal_value(data)


class ProductSerializers(AutoSlugMixin, serializers.ModelSerializer):
    category = ProductCategoryField(queryset=Category.objects.order_by("name"))

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
