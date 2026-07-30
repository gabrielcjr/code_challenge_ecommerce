from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.products.models import CategoryChoices, Product
from apps.products.services import ProductService


class ProductServiceTest(TestCase):
    def setUp(self):
        self.product_data = {
            "name": "Test Product",
            "sku": "TEST-001",
            "description": "Test description",
            "category": CategoryChoices.ELECTRONICS,
            "price": Decimal("99.99"),
            "stock": 10,
            "weight_kg": Decimal("1.500"),
        }
        self.product = Product.objects.create(**self.product_data)

    def test_create_product(self):
        data = {
            "name": "New Product",
            "sku": "NEW-001",
            "description": "New desc",
            "category": CategoryChoices.BOOKS,
            "price": Decimal("20.00"),
            "stock": 5,
            "weight_kg": Decimal("0.5"),
        }
        product = ProductService.create_product(data)
        self.assertEqual(product.name, "New Product")
        self.assertEqual(Product.objects.count(), 2)

    def test_update_product(self):
        updated = ProductService.update_product(
            self.product.id, {"name": "Updated Name", "price": Decimal("150.00")}
        )
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.price, Decimal("150.00"))

    def test_delete_product(self):
        ProductService.delete_product(self.product.id)
        self.assertEqual(Product.objects.count(), 0)

    def test_list_products_no_filter(self):
        result = ProductService.list_products()
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["products"]), 1)

    def test_list_products_with_search(self):
        Product.objects.create(
            name="Another Item",
            sku="OTHER-001",
            description="Different",
            category=CategoryChoices.BOOKS,
            price=Decimal("10.00"),
            stock=5,
            weight_kg=Decimal("0.2"),
        )
        result = ProductService.list_products(query="Test")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["products"][0].sku, "TEST-001")

    def test_list_products_exact_sku_search_precision(self):
        Product.objects.create(
            name="Protein Powder",
            sku="PP-012",
            description="Whey protein isolate",
            category=CategoryChoices.OTHER,
            price=Decimal("34.99"),
            stock=400,
            weight_kg=Decimal("2.0"),
        )
        Product.objects.create(
            name="Mini Projector",
            sku="PRJ-001",
            description="1080p Portable projector",
            category=CategoryChoices.ELECTRONICS,
            price=Decimal("199.99"),
            stock=30,
            weight_kg=Decimal("1.2"),
        )
        result = ProductService.list_products(query="PRJ-001")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["products"][0].sku, "PRJ-001")

    def test_list_products_category_filter(self):
        Product.objects.create(
            name="Book Item",
            sku="BOOK-001",
            description="Book",
            category=CategoryChoices.BOOKS,
            price=Decimal("10.00"),
            stock=5,
            weight_kg=Decimal("0.2"),
        )
        result = ProductService.list_products(category="BOOKS")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["products"][0].category, "BOOKS")

    def test_list_products_price_filter(self):
        result = ProductService.list_products(min_price="50", max_price="150")
        self.assertEqual(result["total"], 1)
        result = ProductService.list_products(min_price="200")
        self.assertEqual(result["total"], 0)

    def test_list_products_in_stock_filter(self):
        Product.objects.create(
            name="Out of stock",
            sku="OOS-001",
            description="",
            category=CategoryChoices.OTHER,
            price=Decimal("5.00"),
            stock=0,
            weight_kg=Decimal("0.1"),
        )
        result = ProductService.list_products(in_stock="true")
        self.assertEqual(result["total"], 1)
        result = ProductService.list_products(in_stock="false")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["products"][0].sku, "OOS-001")

    def test_import_csv_success(self):
        csv_content = (
            b"name,sku,description,category,price,stock,weight_kg\n"
            b"Test CSV,CSV-001,Desc,ELECTRONICS,10.50,100,0.5\n"
        )
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        result = ProductService.import_products_from_csv(csv_file)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["errors"]), 0)
        self.assertTrue(Product.objects.filter(sku="CSV-001").exists())

    def test_import_csv_update_existing(self):
        csv_content = (
            b"name,sku,description,category,price,stock,weight_kg\n"
            b"Updated Product,TEST-001,New desc,ELECTRONICS,200.00,50,1.0\n"
        )
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        result = ProductService.import_products_from_csv(csv_file)
        self.assertEqual(result["updated"], 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Product")

    def test_import_csv_missing_fields(self):
        csv_content = b"name,description\nOnly Name,Desc\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        with self.assertRaises(ValidationError):
            ProductService.import_products_from_csv(csv_file)

    def test_import_csv_invalid_price(self):
        csv_content = b"name,sku,price,stock\nBad Price,BP-001,not-a-price,10\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        result = ProductService.import_products_from_csv(csv_file)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["created"], 0)

    def test_import_csv_empty_file(self):
        csv_file = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        with self.assertRaises(ValidationError):
            ProductService.import_products_from_csv(csv_file)

    def test_import_csv_multiple_rows_with_errors(self):
        csv_content = (
            b"name,sku,price,stock,category\n"
            b"Good Product,GOOD-001,10.00,5,ELECTRONICS\n"
            b"Bad Product,BAD-001,invalid,10,BOOKS\n"
            b"Another Good,GOOD-002,20.00,3,HOME\n"
        )
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        result = ProductService.import_products_from_csv(csv_file)
        self.assertEqual(result["created"], 2)
        self.assertEqual(len(result["errors"]), 1)

    def test_import_csv_sanitizes_xss_and_formula_injection(self):
        csv_content = (
            b"name,sku,description,category,price,stock,weight_kg\n"
            b"<script>alert('xss')</script>,XS-001,Desc,ELECTRONICS,19.99,10,0.1\n"
            b"=cmd|' /C calc'!A0,FORM-001,Formula test,BOOKS,5.00,10,0.1\n"
        )
        csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        result = ProductService.import_products_from_csv(csv_file)
        self.assertEqual(result["created"], 2)

        xss_product = Product.objects.get(sku="XS-001")
        self.assertNotIn("<script>", xss_product.name)

        formula_product = Product.objects.get(sku="FORM-001")
        self.assertFalse(formula_product.name.startswith("="))
