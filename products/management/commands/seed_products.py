
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from ...models import Category, Product


class Command(BaseCommand):
    help = "Populate the database with sample categories and products"

    def handle(self, *args, **kwargs):

        data = {
            "Electronics": [
                ("Wireless Mouse", 1200, 30),
                ("Mechanical Keyboard", 4500, 15),
                ("USB-C Hub", 2500, 20),
                ("Bluetooth Speaker", 3500, 12),
                ("Power Bank 10000mAh", 2800, 25),
                ("Phone Tripod", 1500, 18),
                ("Webcam 1080p", 3200, 10),
                ("Laptop Stand", 1800, 22),
                ("Gaming Headset", 4200, 14),
                ("USB-C Charging Cable", 600, 50),
            ],

            "Clothing": [
                ("Cotton T-Shirt", 850, 40),
                ("Slim Fit Jeans", 2200, 25),
                ("Zip Hoodie", 2500, 20),
                ("Running Shorts", 950, 35),
                ("Denim Jacket", 3800, 12),
                ("Polo Shirt", 1400, 30),
                ("Winter Beanie", 450, 45),
                ("Sports Socks Pack", 500, 50),
                ("Casual Sweatshirt", 1900, 22),
                ("Lightweight Raincoat", 2600, 15),
            ],

            "Books": [
                ("Python Basics Handbook", 1200, 20),
                ("Django Web Development", 1800, 15),
                ("REST API Design Guide", 1500, 18),
                ("Machine Learning Primer", 2200, 12),
                ("Database Systems Intro", 1700, 16),
                ("Clean Code Practices", 1900, 14),
                ("Java Programming Guide", 1600, 20),
                ("Cloud Computing Basics", 2100, 10),
                ("Data Structures Workbook", 1400, 22),
                ("Linux Command Line Guide", 1300, 18),
            ],

            "Home & Kitchen": [
                ("Ceramic Coffee Mug", 550, 35),
                ("Stainless Water Bottle", 1100, 28),
                ("Electric Kettle", 2400, 15),
                ("Nonstick Frying Pan", 1800, 20),
                ("Wooden Cutting Board", 850, 25),
                ("Food Storage Set", 1200, 30),
                ("LED Desk Lamp", 1600, 18),
                ("Pillow Cover Set", 750, 40),
                ("Wall Clock", 950, 22),
                ("Cotton Bath Towel", 700, 35),
            ],

            "Sports & Fitness": [
                ("Yoga Mat", 1300, 25),
                ("Resistance Band Set", 1100, 30),
                ("Jump Rope", 450, 40),
                ("Dumbbell 5kg", 2500, 20),
                ("Foam Roller", 1500, 18),
                ("Gym Gloves", 900, 35),
                ("Sports Water Bottle", 750, 40),
                ("Badminton Racket", 2200, 16),
                ("Football Size 5", 1800, 22),
                ("Running Armband", 650, 30),
            ],
        }

        categories_created = 0
        products_created = 0

        with transaction.atomic():
            for category_name, products in data.items():

                category, created = Category.objects.get_or_create(
                    name=category_name,
                    defaults={
                        "slug": slugify(category_name),
                        "description": f"Products related to {category_name}",
                    }
                )

                if created:
                    categories_created += 1

                for name, price, stock in products:

                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            "slug": slugify(name),
                            "description": (
                                f"{name} from our {category_name} collection."
                            ),
                            "price": price,
                            "stock": stock,
                            "category": category,
                        }
                    )

                    if created:
                        products_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {categories_created} categories and "
                f"{products_created} products successfully!"
            )
        )
