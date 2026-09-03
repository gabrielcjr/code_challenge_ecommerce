import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.orders.models import Order, OrderItem, PaymentStatus
from apps.orders.services import OrderService
from apps.products.models import CategoryChoices, Product


def _purchase(product_id, quantity, email):
    try:
        order = OrderService.single_product_purchase(
            product_id=product_id,
            quantity=quantity,
            customer_info={
                "customer_name": "Concurrent Buyer",
                "customer_email": email,
                "simulate_failure": False,
            },
        )
        return ("ok", order.id)
    except ValidationError as exc:
        return ("rejected", str(exc))
    finally:
        connections.close_all()


@skipUnlessDBFeature("has_select_for_update")
class InventoryConcurrencyTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.product = Product.objects.create(
            name="Limited Edition",
            sku="LIM-001",
            description="Scarce inventory",
            category=CategoryChoices.ELECTRONICS,
            price=Decimal("100.00"),
            stock=10,
            weight_kg=Decimal("1.000"),
        )

    def test_concurrent_buyers_cannot_oversell_stock(self):
        buyers = 20
        with ThreadPoolExecutor(max_workers=buyers) as pool:
            outcomes = list(
                pool.map(
                    lambda i: _purchase(self.product.id, 1, f"buyer{i}@example.com"),
                    range(buyers),
                )
            )

        accepted = [o for o in outcomes if o[0] == "ok"]
        rejected = [o for o in outcomes if o[0] == "rejected"]

        self.product.refresh_from_db()
        self.assertEqual(len(accepted), 10)
        self.assertEqual(len(rejected), 10)
        self.assertEqual(self.product.stock, 0)
        self.assertTrue(
            all("Insufficient stock" in message for _, message in rejected)
        )

    def test_stock_never_goes_negative_with_uneven_quantities(self):
        quantities = [4, 3, 3, 5, 2, 6, 1, 4]
        with ThreadPoolExecutor(max_workers=len(quantities)) as pool:
            outcomes = list(
                pool.map(
                    lambda item: _purchase(
                        self.product.id, item[1], f"uneven{item[0]}@example.com"
                    ),
                    enumerate(quantities),
                )
            )

        self.product.refresh_from_db()
        sold = sum(
            OrderItem.objects.filter(product=self.product).values_list(
                "quantity", flat=True
            )
        )

        self.assertGreaterEqual(self.product.stock, 0)
        self.assertEqual(self.product.stock, 10 - sold)
        self.assertTrue(any(status == "ok" for status, _ in outcomes))

    def test_orders_and_stock_stay_consistent_under_load(self):
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(
                pool.map(
                    lambda i: _purchase(self.product.id, 2, f"load{i}@example.com"),
                    range(10),
                )
            )

        self.product.refresh_from_db()
        paid_items = OrderItem.objects.filter(
            product=self.product, order__payment_status=PaymentStatus.PAID
        )
        sold = sum(paid_items.values_list("quantity", flat=True))

        self.assertEqual(sold, 10 - self.product.stock)
        self.assertEqual(Order.objects.filter(payment_status=PaymentStatus.PAID).count(), 5)

    def test_multi_product_orders_do_not_deadlock(self):
        second = Product.objects.create(
            name="Companion Item",
            sku="LIM-002",
            description="Second scarce item",
            category=CategoryChoices.ELECTRONICS,
            price=Decimal("50.00"),
            stock=10,
            weight_kg=Decimal("0.500"),
        )
        ids = [self.product.id, second.id]

        def buy(order_of_ids, index):
            try:
                OrderService.create_and_process_order(
                    items_data=[
                        {"product_id": pid, "quantity": 1} for pid in order_of_ids
                    ],
                    customer_info={
                        "customer_name": "Deadlock Probe",
                        "customer_email": f"probe{index}@example.com",
                        "simulate_failure": False,
                    },
                )
                return "ok"
            except ValidationError:
                return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(
                pool.map(
                    lambda i: buy(ids if i % 2 == 0 else list(reversed(ids)), i),
                    range(8),
                )
            )

        self.assertEqual(outcomes.count("ok"), 8)
        self.product.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(second.stock, 2)

    def test_second_buyer_blocks_until_first_transaction_commits(self):
        first_locked = threading.Event()
        release_first = threading.Event()
        observed = {}

        def slow_buyer():
            from django.db import transaction

            try:
                with transaction.atomic():
                    locked = (
                        Product.objects.select_for_update()
                        .filter(id=self.product.id)
                        .order_by("id")
                        .first()
                    )
                    first_locked.set()
                    release_first.wait(timeout=10)
                    locked.stock -= 10
                    locked.save(update_fields=["stock", "updated_at"])
            finally:
                connections.close_all()

        def waiting_buyer():
            first_locked.wait(timeout=10)
            observed["result"] = _purchase(
                self.product.id, 5, "waiter@example.com"
            )

        holder = threading.Thread(target=slow_buyer)
        waiter = threading.Thread(target=waiting_buyer)
        holder.start()
        waiter.start()
        first_locked.wait(timeout=10)
        release_first.set()
        holder.join(timeout=15)
        waiter.join(timeout=15)

        self.product.refresh_from_db()
        self.assertEqual(observed["result"][0], "rejected")
        self.assertIn("Insufficient stock", observed["result"][1])
        self.assertEqual(self.product.stock, 0)


@skipUnlessDBFeature("has_select_for_update")
class FailedPaymentPersistenceTest(TransactionTestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Declined Item",
            sku="DEC-001",
            description="Payment always fails",
            category=CategoryChoices.OTHER,
            price=Decimal("25.00"),
            stock=5,
            weight_kg=Decimal("0.250"),
        )

    def test_failed_payment_records_order_and_leaves_stock_untouched(self):
        with self.assertRaises(ValidationError):
            OrderService.single_product_purchase(
                product_id=self.product.id,
                quantity=2,
                customer_info={
                    "customer_name": "Declined Buyer",
                    "customer_email": "declined@example.com",
                    "simulate_failure": True,
                },
            )

        self.product.refresh_from_db()
        failed = Order.objects.filter(payment_status=PaymentStatus.FAILED)

        self.assertEqual(self.product.stock, 5)
        self.assertEqual(failed.count(), 1)
        self.assertEqual(failed.first().items.count(), 1)
