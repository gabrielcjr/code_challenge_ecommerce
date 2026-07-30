from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.orders.models import Order, OrderItem
from apps.products.models import CategoryChoices, Product


class Command(BaseCommand):
    help = "Seed database with sample products"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh", action="store_true", help="Clear existing data before seeding"
        )

    def handle(self, *args, **options):
        refresh = options.get("refresh", False)

        if refresh:
            self.stdout.write("Clearing existing data...")
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING("Database cleared"))

        sample_products = [
            {
                "name": 'MacBook Pro 16" M3 Max',
                "sku": "MBP-16-M3-001",
                "description": (
                    "Apple MacBook Pro with M3 Max chip, 64GB RAM, 1TB SSD, "
                    "perfect for enterprise development and creative workloads"
                ),
                "category": CategoryChoices.ELECTRONICS,
                "price": Decimal("3999.99"),
                "stock": 25,
                "weight_kg": Decimal("2.100"),
            },
            {
                "name": "Sony WH-1000XM5 Headphones",
                "sku": "SONY-WH-1000XM5",
                "description": (
                    "Industry leading noise canceling headphones with "
                    "premium sound quality and 30hr battery"
                ),
                "category": CategoryChoices.ELECTRONICS,
                "price": Decimal("399.99"),
                "stock": 120,
                "weight_kg": Decimal("0.250"),
            },
            {
                "name": "Ergonomic Office Chair",
                "sku": "CHAIR-ERG-007",
                "description": (
                    "Full mesh ergonomic chair with lumbar support, "
                    "adjustable armrests, ideal for long work sessions"
                ),
                "category": CategoryChoices.HOME,
                "price": Decimal("549.00"),
                "stock": 40,
                "weight_kg": Decimal("18.500"),
            },
            {
                "name": "Design Patterns Book",
                "sku": "BOOK-DP-GOF-001",
                "description": (
                    "Gang of Four classic design patterns enterprise "
                    "edition with Python examples"
                ),
                "category": CategoryChoices.BOOKS,
                "price": Decimal("59.99"),
                "stock": 200,
                "weight_kg": Decimal("0.800"),
            },
            {
                "name": "Premium Cotton T-Shirt",
                "sku": "TSHIRT-PREM-WHT-M",
                "description": (
                    "100% organic cotton heavyweight t-shirt, minimalist "
                    "design, sustainable production"
                ),
                "category": CategoryChoices.CLOTHING,
                "price": Decimal("29.99"),
                "stock": 500,
                "weight_kg": Decimal("0.200"),
            },
            {
                "name": "Mechanical Keyboard K8",
                "sku": "KB-MECH-K8-001",
                "description": (
                    "TKL hot-swappable mechanical keyboard with PBT keycaps "
                    "and wireless connectivity"
                ),
                "category": CategoryChoices.ELECTRONICS,
                "price": Decimal("129.90"),
                "stock": 85,
                "weight_kg": Decimal("1.100"),
            },
            {
                "name": "Smart Water Bottle",
                "sku": "BOTTLE-SMART-32OZ",
                "description": (
                    "Insulated smart bottle with hydration tracking and "
                    "temperature control"
                ),
                "category": CategoryChoices.HOME,
                "price": Decimal("45.50"),
                "stock": 150,
                "weight_kg": Decimal("0.350"),
            },
            {
                "name": "Python Deep Dive Course",
                "sku": "BOOK-PY-ADV-002",
                "description": (
                    "Advanced Python programming with enterprise patterns, "
                    "async and testing"
                ),
                "category": CategoryChoices.BOOKS,
                "price": Decimal("79.00"),
                "stock": 1000,
                "weight_kg": Decimal("0.001"),
            },
            {
                "name": "Wireless Charging Pad",
                "sku": "CHARGER-WRL-15W",
                "description": (
                    "Fast wireless charger 15W compatible with all Qi devices, "
                    "aluminum finish"
                ),
                "category": CategoryChoices.ELECTRONICS,
                "price": Decimal("39.99"),
                "stock": 300,
                "weight_kg": Decimal("0.150"),
            },
            {
                "name": "Linen Blend Blazer",
                "sku": "BLAZER-LINEN-NAV-42",
                "description": (
                    "Modern linen blazer for business casual, "
                    "breathable and lightweight"
                ),
                "category": CategoryChoices.CLOTHING,
                "price": Decimal("199.00"),
                "stock": 30,
                "weight_kg": Decimal("0.900"),
            },
        ]

        created = 0
        with transaction.atomic():
            for data in sample_products:
                _, was_created = Product.objects.get_or_create(
                    sku=data["sku"], defaults=data
                )
                if was_created:
                    created += 1

        total = Product.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} new products, total {total} products")
        )
