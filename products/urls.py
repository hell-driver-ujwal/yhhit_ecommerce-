from django.urls import path, include 
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('category', views.CategoryViewset, basename= 'category')

urlpatterns =[
    path('api/', include(router.urls)),
    path('', views.store, name = 'store'),
    path('category/<slug:category_slug>', views.store, name = 'store')
]