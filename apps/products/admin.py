from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "price", "stock", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["name", "sku", "description"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
