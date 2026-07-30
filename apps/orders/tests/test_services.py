from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.orders.models import Order, PaymentStatus
from apps.orders.services import OrderService, PaymentService
from apps.products.models import CategoryChoices, Product


class PaymentServiceTest(TestCase):
    def test_process_payment_success(self):
        result = PaymentService.process_payment(
            Decimal("100.00"), "test@example.com", simulate_failure=False
        )
        self.assertIn("transaction_id", result)
        self.assertIn("amount", result)
        self.assertEqual(result["amount"], Decimal("100.00"))

    def test_process_payment_failure_simulated(self):
        result = PaymentService.process_payment(
            Decimal("100.00"), "test@example.com", simulate_failure=True
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], PaymentStatus.FAILED)

    def test_validate_card_data_valid(self):
        self.assertTrue(
            PaymentService.validate_card_data("4242424242424242", "123", "12/30")
        )

    def test_validate_card_data_invalid_number(self):
        with self.assertRaises(ValidationError):
            PaymentService.validate_card_data("123", "123", "12/30")

    def test_validate_card_data_invalid_cvv(self):
        with self.assertRaises(ValidationError):
            PaymentService.validate_card_data("4242424242424242", "1", "12/30")

    def test_validate_card_data_invalid_expiry(self):
        with self.assertRaises(ValidationError):
            PaymentService.validate_card_data("4242424242424242", "123", "1230")


class OrderServiceTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            description="Test",
            category=CategoryChoices.ELECTRONICS,
            price=Decimal("50.00"),
            stock=10,
            weight_kg=Decimal("1.0"),
        )
        self.product2 = Product.objects.create(
            name="Second Product",
            sku="TEST-002",
            description="Second",
            category=CategoryChoices.BOOKS,
            price=Decimal("25.00"),
            stock=5,
            weight_kg=Decimal("0.5"),
        )

    def test_create_order_single_product(self):
        order = OrderService.create_and_process_order(
            items_data=[{"product_id": self.product.id, "quantity": 2}],
            customer_info={
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "simulate_failure": False,
            },
        )
        self.assertEqual(order.total_amount, Decimal("100.00"))
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        self.assertEqual(order.items.count(), 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_create_order_multiple_products(self):
        order = OrderService.create_and_process_order(
            items_data=[
                {"product_id": self.product.id, "quantity": 1},
                {"product_id": self.product2.id, "quantity": 2},
            ],
            customer_info={
                "customer_name": "Jane Doe",
                "customer_email": "jane@example.com",
                "simulate_failure": False,
            },
        )
        self.assertEqual(order.total_amount, Decimal("100.00"))
        self.assertEqual(order.items.count(), 2)

        self.product.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(self.product2.stock, 3)

    def test_create_order_insufficient_stock(self):
        with self.assertRaises(ValidationError) as ctx:
            OrderService.create_and_process_order(
                items_data=[{"product_id": self.product.id, "quantity": 20}],
                customer_info={
                    "customer_name": "John",
                    "customer_email": "john@example.com",
                },
            )
        self.assertIn("Insufficient stock", str(ctx.exception))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_create_order_missing_customer_info(self):
        with self.assertRaises(ValidationError):
            OrderService.create_and_process_order(
                items_data=[{"product_id": self.product.id, "quantity": 1}],
                customer_info={
                    "customer_name": "",
                    "customer_email": "john@example.com",
                },
            )

        with self.assertRaises(ValidationError):
            OrderService.create_and_process_order(
                items_data=[{"product_id": self.product.id, "quantity": 1}],
                customer_info={"customer_name": "John", "customer_email": ""},
            )

    def test_create_order_payment_failure(self):
        with self.assertRaises(ValidationError) as ctx:
            OrderService.create_and_process_order(
                items_data=[{"product_id": self.product.id, "quantity": 1}],
                customer_info={
                    "customer_name": "John Doe",
                    "customer_email": "john@example.com",
                    "simulate_failure": True,
                },
            )
        self.assertIn("Payment failed", str(ctx.exception))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

        failed_orders = Order.objects.filter(payment_status=PaymentStatus.FAILED)
        self.assertEqual(failed_orders.count(), 1)

    def test_single_product_purchase(self):
        order = OrderService.single_product_purchase(
            product_id=self.product.id,
            quantity=3,
            customer_info={
                "customer_name": "Alice",
                "customer_email": "alice@example.com",
                "simulate_failure": False,
            },
        )
        self.assertEqual(order.total_amount, Decimal("150.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_get_order(self):
        created = OrderService.single_product_purchase(
            product_id=self.product.id,
            quantity=1,
            customer_info={
                "customer_name": "Bob",
                "customer_email": "bob@example.com",
                "simulate_failure": False,
            },
        )
        fetched = OrderService.get_order(created.id)
        self.assertEqual(fetched.id, created.id)

    def test_list_orders(self):
        OrderService.single_product_purchase(
            product_id=self.product.id,
            quantity=1,
            customer_info={
                "customer_name": "Bob",
                "customer_email": "bob@example.com",
                "simulate_failure": False,
            },
        )
        OrderService.single_product_purchase(
            product_id=self.product.id,
            quantity=1,
            customer_info={
                "customer_name": "Alice",
                "customer_email": "alice@example.com",
                "simulate_failure": False,
            },
        )
        all_orders = OrderService.list_orders()
        self.assertEqual(all_orders.count(), 2)

        filtered = OrderService.list_orders(customer_email="bob@example.com")
        self.assertEqual(filtered.count(), 1)

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValidationError):
            OrderService.create_and_process_order(
                items_data=[{"product_id": self.product.id, "quantity": 0}],
                customer_info={
                    "customer_name": "John",
                    "customer_email": "john@example.com",
                },
            )

    def test_nonexistent_product_raises(self):
        with self.assertRaises(ValidationError):
            OrderService.create_and_process_order(
                items_data=[{"product_id": 99999, "quantity": 1}],
                customer_info={
                    "customer_name": "John",
                    "customer_email": "john@example.com",
                },
            )
