from rest_framework import serializers
from .models import Product, Category
from django.utils.text import slugify

class AutoSlugMixin:
    def create(slef, validate_data):
        validate_data['slug']= slugify(validate_data['name'])
        return super().create(validate_data)

    def update(self, instance ,validate_data ):
        if 'name' in validate_data:
            validate_data['slug']= slugify(validate_data['name'])
            return super().update(validate_data)

class ProductSerializers(AutoSlugMixin, serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['slug']
    

class CategorySerializers(AutoSlugMixin, serializers.ModelSerializer):

    # nested ?
    products = ProductSerializers(many = True, read_only = True)
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['slug']