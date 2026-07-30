from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.orders.models import Order, PaymentStatus
from apps.products.models import CategoryChoices, Product


class OrderViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-001",
            description="Test description",
            category=CategoryChoices.ELECTRONICS,
            price=Decimal("99.99"),
            stock=10,
            weight_kg=Decimal("1.5"),
        )

    def test_checkout_modal(self):
        response = self.client.get(
            reverse("checkout-modal", args=[self.product.id]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checkout")
        self.assertContains(response, "Test Product")

    def test_process_checkout_get(self):
        response = self.client.get(
            reverse("process-checkout", args=[self.product.id]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

    @patch("apps.orders.services.PaymentService.process_payment")
    def test_process_checkout_success(self, mock_payment):
        mock_payment.return_value = {
            "success": True,
            "transaction_id": "txn_test_success_12345",
            "status": PaymentStatus.PAID,
            "message": "Payment processed successfully",
            "amount": Decimal("199.98"),
        }
        data = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "quantity": "2",
            "card_number": "4242 4242 4242 4242",
            "card_expiry": "12/30",
            "card_cvv": "123",
        }
        response = self.client.post(
            reverse("process-checkout", args=[self.product.id]),
            data,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Order.objects.filter(customer_email="john@example.com").exists()
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_process_checkout_insufficient_stock(self):
        data = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "quantity": "20",
            "card_number": "4242 4242 4242 4242",
            "card_expiry": "12/30",
            "card_cvv": "123",
        }
        response = self.client.post(
            reverse("process-checkout", args=[self.product.id]),
            data,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 10 items available")

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_process_checkout_invalid_form(self):
        data = {
            "customer_name": "",
            "customer_email": "invalid-email",
            "quantity": "0",
        }
        response = self.client.post(
            reverse("process-checkout", args=[self.product.id]),
            data,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_list(self):
        response = self.client.get(reverse("order-list"))
        self.assertEqual(response.status_code, 200)

    def test_order_detail(self):
        order = Order.objects.create(
            transaction_id="txn_test123",
            customer_name="Test",
            customer_email="test@example.com",
            total_amount=Decimal("99.99"),
            payment_status=PaymentStatus.PAID,
        )
        response = self.client.get(reverse("order-detail", args=[order.transaction_id]))
        self.assertEqual(response.status_code, 200)
