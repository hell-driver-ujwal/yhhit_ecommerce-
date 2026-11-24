from django.shortcuts import render
from rest_framework import viewsets , generics , mixins
from .models import Product, Category
from django.shortcuts import get_object_or_404 
from .serializers import CategorySerializers, ProductSerializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


# Create your views here.
class CategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializers


@api_view(['GET','POST'])
def store(request, category_slug = None):
    products = Product.objects.all()

    if request.method == 'GET':
        if category_slug is not None:
            category = get_object_or_404(Category, slug = category_slug)
            products = Product.objects.filter(category = category)

        serializer = ProductSerializers(products, many = True)
        return Response(serializer.data, status= status.HTTP_200_OK)

    elif request.method == 'POST':
        if category_slug is not None:
            return Response(
                {"detail":"Use api/products to create products"}
            ) 
        
        serializer = ProductSerializers(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_201_CREATED)
        
    
