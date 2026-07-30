from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_id",
        "customer_name",
        "customer_email",
        "total_amount",
        "payment_status",
        "created_at",
    ]
    list_filter = ["payment_status", "created_at"]
    search_fields = ["transaction_id", "customer_email", "customer_name"]
    ordering = ["-created_at"]
    inlines = [OrderItemInline]
    readonly_fields = ["transaction_id", "created_at", "updated_at"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "unit_price", "subtotal"]
    list_filter = ["created_at"]
    search_fields = ["order__transaction_id", "product__name"]
