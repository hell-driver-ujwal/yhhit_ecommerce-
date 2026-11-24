from django.db import models

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length= 50, unique= True)
    slug = models.SlugField(max_length= 50, unique= True)
    description = models.TextField(max_length= 255, blank= True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'category' 
        verbose_name_plural = 'catrgories'

# Each product should have a name, description, price, stock quantity, category, and image (optional).
class Product(models.Model):
    name = models.CharField(max_length= 30, unique= True)
    slug = models.SlugField(max_length= 30, unique= True)
    description = models.TextField(max_length= 255, blank= True)
    price = models.IntegerField()
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name= 'products')

    def __str__(self):
        return self.name

