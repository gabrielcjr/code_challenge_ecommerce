
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("sku", models.CharField(db_index=True, max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("ELECTRONICS", "Electronics"),
                            ("CLOTHING", "Clothing"),
                            ("HOME", "Home"),
                            ("BOOKS", "Books"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=20,
                    ),
                ),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("stock", models.PositiveIntegerField(default=0)),
                (
                    "weight_kg",
                    models.DecimalField(decimal_places=3, default=0, max_digits=8),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["sku"], name="products_pr_sku_ca0cdc_idx"),
                    models.Index(
                        fields=["category"], name="products_pr_categor_14b9c0_idx"
                    ),
                    models.Index(fields=["price"], name="products_pr_price_9b1a5f_idx"),
                    models.Index(
                        fields=["created_at"], name="products_pr_created_52f0d7_idx"
                    ),
                ],
            },
        ),
    ]
