from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.products.models import CategoryChoices, Product


class ProductViewsTest(TestCase):
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

    def test_product_list_page(self):
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")
        self.assertContains(response, "TEST-001")

    def test_product_search_htmx(self):
        response = self.client.get(
            reverse("product-search"), {"q": "Test"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

        response = self.client.get(
            reverse("product-search"), {"q": "Nonexistent"}, HTTP_HX_REQUEST="true"
        )
        self.assertContains(response, "No products found")

    def test_product_create_modal(self):
        response = self.client.get(
            reverse("product-create-modal"), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Product")

    def test_product_create_success(self):
        data = {
            "name": "New Product",
            "sku": "NEW-001",
            "description": "New",
            "category": "BOOKS",
            "price": "25.00",
            "stock": "10",
            "weight_kg": "0.5",
        }
        response = self.client.post(
            reverse("product-create"), data, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.filter(sku="NEW-001").exists())

    def test_product_create_invalid(self):
        data = {
            "name": "",
            "sku": "",
            "price": "-10",
            "stock": "-5",
        }
        response = self.client.post(
            reverse("product-create"), data, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 1)

    def test_product_edit_modal(self):
        response = self.client.get(
            reverse("product-edit-modal", args=[self.product.id]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

    def test_product_update_success(self):
        data = {
            "name": "Updated Product",
            "sku": "TEST-001",
            "description": "Updated",
            "category": "HOME",
            "price": "199.99",
            "stock": "20",
            "weight_kg": "2.0",
        }
        response = self.client.post(
            reverse("product-update", args=[self.product.id]),
            data,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Product")
        self.assertEqual(self.product.category, "HOME")

    def test_product_delete(self):
        response = self.client.post(
            reverse("product-delete", args=[self.product.id]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Product.objects.count(), 0)

    def test_csv_import_modal(self):
        response = self.client.get(reverse("csv-import-modal"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Products")

    def test_product_list_filter_category(self):
        response = self.client.get(reverse("product-list"), {"category": "ELECTRONICS"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")

        response = self.client.get(reverse("product-list"), {"category": "BOOKS"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Product")

    def test_product_detail_htmx(self):
        response = self.client.get(
            reverse("product-detail", args=[self.product.id]), HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Product")
