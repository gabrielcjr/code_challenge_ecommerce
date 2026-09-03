import random
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.products.models import Product

from .models import Order, OrderItem, PaymentStatus


class PaymentService:

    @staticmethod
    def process_payment(
        amount: Decimal, customer_email: str, simulate_failure=None
    ) -> Dict[str, Any]:
        time.sleep(0.1)

        should_fail = False
        if simulate_failure is True:
            should_fail = True
        elif simulate_failure is False:
            should_fail = False
        else:
            should_fail = random.random() < 0.05

        if should_fail:
            return {
                "success": False,
                "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
                "status": PaymentStatus.FAILED,
                "message": "Payment declined by simulated gateway",
                "amount": amount,
            }

        return {
            "success": True,
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "status": PaymentStatus.PAID,
            "message": "Payment processed successfully",
            "amount": amount,
        }

    @staticmethod
    def validate_card_data(card_number: str, cvv: str, expiry: str) -> bool:
        if not card_number or len(card_number.replace(" ", "")) < 13:
            raise ValidationError("Invalid card number")
        if not cvv or len(cvv) < 3:
            raise ValidationError("Invalid CVV")
        if not expiry or "/" not in expiry:
            raise ValidationError("Invalid expiry date format MM/YY")
        return True


class OrderService:

    @staticmethod
    def create_and_process_order(
        items_data: List[Dict[str, Any]], customer_info: Dict[str, Any]
    ) -> Order:
        if not items_data:
            raise ValidationError("Order must contain at least one item")

        customer_name = customer_info.get("customer_name", "").strip()
        customer_email = customer_info.get("customer_email", "").strip()
        simulate_failure = customer_info.get("simulate_failure", None)

        if not customer_name:
            raise ValidationError("Customer name is required")
        if not customer_email:
            raise ValidationError("Customer email is required")

        product_ids = [item["product_id"] for item in items_data]

        with transaction.atomic():
            products = (
                Product.objects.select_for_update()
                .filter(id__in=product_ids)
                .order_by("id")
            )
            product_map = {p.id: p for p in products}

            if len(product_map) != len(set(product_ids)):
                missing = set(product_ids) - set(product_map.keys())
                raise ValidationError(f"Products not found: {missing}")

            total_amount = Decimal("0.00")
            order_items_to_create = []

            for item in items_data:
                product_id = item["product_id"]
                quantity = item.get("quantity", 1)

                if quantity <= 0:
                    raise ValidationError(
                        f"Quantity must be positive for product {product_id}"
                    )

                product = product_map[product_id]

                if product.stock < quantity:
                    raise ValidationError(
                        f"Insufficient stock for {product.name}. "
                        f"Available: {product.stock}, Requested: {quantity}"
                    )

                item_total = product.price * quantity
                total_amount += item_total

                order_items_to_create.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "unit_price": product.price,
                    }
                )

            payment_result = PaymentService.process_payment(
                amount=total_amount,
                customer_email=customer_email,
                simulate_failure=simulate_failure,
            )

            if not payment_result["success"]:
                failure_ctx = {
                    "transaction_id": payment_result["transaction_id"],
                    "message": payment_result["message"],
                    "total_amount": total_amount,
                    "items": order_items_to_create,
                }
            else:
                order = Order.objects.create(
                    transaction_id=payment_result["transaction_id"],
                    customer_name=customer_name,
                    customer_email=customer_email,
                    total_amount=total_amount,
                    payment_status=PaymentStatus.PAID,
                )

                for item_data in order_items_to_create:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data["product"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                    )
                    prod = item_data["product"]
                    prod.stock -= item_data["quantity"]
                    prod.save(update_fields=["stock", "updated_at"])

                return order

        with transaction.atomic():
            order = Order.objects.create(
                transaction_id=failure_ctx["transaction_id"],
                customer_name=customer_name,
                customer_email=customer_email,
                total_amount=failure_ctx["total_amount"],
                payment_status=PaymentStatus.FAILED,
            )
            for item_data in failure_ctx["items"]:
                OrderItem.objects.create(
                    order=order,
                    product=item_data["product"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                )

        raise ValidationError(f"Payment failed: {failure_ctx['message']}")

    @staticmethod
    def get_order(order_id: int) -> Order:
        return Order.objects.get(id=order_id)

    @staticmethod
    def get_order_by_transaction_id(transaction_id: str) -> Order:
        return Order.objects.get(transaction_id=transaction_id)

    @staticmethod
    def list_orders(customer_email=None, status=None):
        queryset = Order.objects.prefetch_related("items__product").all()
        if customer_email:
            queryset = queryset.filter(customer_email=customer_email)
        if status:
            queryset = queryset.filter(payment_status=status)
        return queryset

    @staticmethod
    def single_product_purchase(
        product_id: int, quantity: int, customer_info: Dict[str, Any]
    ) -> Order:
        return OrderService.create_and_process_order(
            items_data=[{"product_id": product_id, "quantity": quantity}],
            customer_info=customer_info,
        )
