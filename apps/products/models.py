from django.db import models


class CategoryChoices(models.TextChoices):
    ELECTRONICS = "ELECTRONICS", "Electronics"
    CLOTHING = "CLOTHING", "Clothing"
    HOME = "HOME", "Home"
    BOOKS = "BOOKS", "Books"
    OTHER = "OTHER", "Other"


class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=CategoryChoices.choices, default=CategoryChoices.OTHER
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["category"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def in_stock(self):
        return self.stock > 0
