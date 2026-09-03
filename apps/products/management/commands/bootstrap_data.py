from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.products.models import Product
from apps.products.services import ProductService

DEFAULT_CSV_NAME = "Code Challenge E-Commerce.csv"


class Command(BaseCommand):
    help = "Load the sample catalog on first boot so the app is usable immediately"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=None)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        if Product.objects.exists() and not options["force"]:
            self.stdout.write("Catalog already populated, skipping bootstrap")
            return

        csv_path = Path(options["csv"] or Path(settings.BASE_DIR) / DEFAULT_CSV_NAME)

        if not csv_path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"No CSV at {csv_path}, falling back to the built-in sample catalog"
                )
            )
            call_command("seed")
            return

        with csv_path.open("rb") as handle:
            result = ProductService.import_products_from_csv(handle)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported catalog from {csv_path.name}: "
                f"{result['created']} created, {result['updated']} updated, "
                f"{result['error_count']} rejected"
            )
        )
