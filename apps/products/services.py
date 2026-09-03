import csv
import html
import io
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils.html import strip_tags

from .models import CategoryChoices, Product

CSV_BATCH_SIZE = 500
MAX_REPORTED_ERRORS = 200
PRODUCT_FIELDS = [
    "name",
    "sku",
    "description",
    "category",
    "price",
    "stock",
    "weight_kg",
]


def _sanitize_input_text(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    text = text.replace("\x00", "")
    text = strip_tags(text)
    if text.startswith(("=", "+", "@", "\t", "\r")):
        text = text.lstrip("=+@\t\r").strip()
    return html.escape(text, quote=False)


def _parse_price_value(raw_value: Any, row_num: int) -> Decimal:
    if raw_value is None:
        raise ValidationError(f"Missing price at row {row_num}")

    raw_str = str(raw_value).strip()

    if raw_str == "":
        raise ValidationError(f"Missing price at row {row_num}")

    if raw_str.lower() == "free":
        return Decimal("0")

    cleaned = raw_str
    for sym in ("$", "€", "£", "¥"):
        cleaned = cleaned.replace(sym, "")
    cleaned = cleaned.strip()
    cleaned_without_commas = cleaned.replace(",", "")
    cleaned_without_commas = cleaned_without_commas.strip()

    if cleaned_without_commas.lower() == "free":
        return Decimal("0")

    match = re.search(r"-?\d+(\.\d+)?", cleaned_without_commas)
    if not match:
        match = re.search(r"-?\d+(\.\d+)?", cleaned)

    if not match:
        raise ValidationError(f"Invalid price '{raw_str}' at row {row_num}")

    try:
        price = Decimal(match.group(0))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Invalid price '{raw_str}' at row {row_num}")

    if price < 0:
        raise ValidationError(f"Price cannot be negative at row {row_num}")

    return price


def _parse_stock_value(raw_value: Any, row_num: int) -> int:
    if raw_value is None or str(raw_value).strip() == "":
        raise ValidationError(f"Missing stock at row {row_num}")

    raw_str = str(raw_value).strip()

    if raw_str == "":
        raise ValidationError(f"Missing stock at row {row_num}")

    numeric_match = re.search(r"-?\d+(\.\d+)?", raw_str)

    if not numeric_match:
        raise ValidationError(f"Invalid stock '{raw_str}' at row {row_num}")

    try:
        stock = int(float(numeric_match.group(0)))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid stock '{raw_str}' at row {row_num}")

    if stock < 0:
        raise ValidationError(f"Stock cannot be negative at row {row_num}")

    return stock


def _parse_weight_value(raw_value: Any) -> Decimal:
    if raw_value is None:
        return Decimal("0")

    weight_str = str(raw_value).strip()
    if not weight_str:
        return Decimal("0")

    cleaned = weight_str.replace(",", "").replace("$", "").strip()
    match = re.search(r"-?\d+(\.\d+)?", cleaned)

    if not match:
        return Decimal("0")

    try:
        weight = Decimal(match.group(0))
        return weight if weight >= 0 else Decimal("0")
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


class ProductService:

    @staticmethod
    def list_products(
        query=None,
        category=None,
        min_price=None,
        max_price=None,
        in_stock=None,
        sort_by="-created_at",
        page=1,
        per_page=12,
    ):
        queryset = Product.objects.all()

        has_trigram = False
        if query:
            query_clean = str(query).strip()
            base_q = (
                Q(name__icontains=query_clean)
                | Q(sku__icontains=query_clean)
                | Q(description__icontains=query_clean)
            )
            exact_qs = queryset.filter(base_q)
            if exact_qs.exists():
                queryset = exact_qs
            else:
                try:
                    from django.db import connection

                    if connection.vendor == "postgresql":
                        from django.contrib.postgres.search import TrigramSimilarity

                        queryset = (
                            Product.objects.annotate(
                                similarity=TrigramSimilarity("name", query_clean)
                                + TrigramSimilarity("description", query_clean)
                            )
                            .filter(similarity__gt=0.2)
                            .order_by("-similarity", sort_by)
                        )
                        has_trigram = True
                    else:
                        queryset = exact_qs
                except Exception:
                    queryset = exact_qs

        if category:
            queryset = queryset.filter(category=category)

        if min_price is not None:
            try:
                queryset = queryset.filter(price__gte=Decimal(str(min_price)))
            except (InvalidOperation, ValueError):
                pass

        if max_price is not None:
            try:
                queryset = queryset.filter(price__lte=Decimal(str(max_price)))
            except (InvalidOperation, ValueError):
                pass

        if in_stock is not None:
            if str(in_stock).lower() in ("true", "1", "yes"):
                queryset = queryset.filter(stock__gt=0)
            elif str(in_stock).lower() in ("false", "0", "no"):
                queryset = queryset.filter(stock=0)

        valid_sort_fields = [
            "name",
            "-name",
            "price",
            "-price",
            "created_at",
            "-created_at",
            "stock",
            "-stock",
        ]
        if sort_by not in valid_sort_fields:
            sort_by = "-created_at"

        if not has_trigram:
            queryset = queryset.order_by(sort_by)

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        return {
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "total": paginator.count,
        }

    @staticmethod
    def get_product(product_id: int) -> Product:
        return Product.objects.get(id=product_id)

    @staticmethod
    def create_product(data: Dict[str, Any]) -> Product:
        return Product.objects.create(**data)

    @staticmethod
    def update_product(product_id: int, data: Dict[str, Any]) -> Product:
        product = Product.objects.get(id=product_id)
        for key, value in data.items():
            setattr(product, key, value)
        product.full_clean()
        product.save()
        return product

    @staticmethod
    def delete_product(product_id: int) -> None:
        Product.objects.filter(id=product_id).delete()

    @staticmethod
    def _open_csv_stream(csv_file):
        if hasattr(csv_file, "seekable") and csv_file.seekable():
            csv_file.seek(0)
        return io.TextIOWrapper(csv_file, encoding="utf-8", newline="")

    @staticmethod
    def _flush_batch(batch, counters, errors):
        if not batch:
            return

        skus = [parsed["sku"] for parsed in batch]
        existing_map = {
            product.sku: product
            for product in Product.objects.filter(sku__in=skus).only("id", *PRODUCT_FIELDS)
        }

        to_create = []
        to_update = []

        for row_num, parsed in zip(counters["rows"], batch):
            product = existing_map.get(parsed["sku"])
            if product is None:
                product = Product(**parsed)
            else:
                for key, value in parsed.items():
                    setattr(product, key, value)

            try:
                product.full_clean(validate_unique=False)
            except ValidationError as exc:
                ProductService._record_error(
                    errors,
                    row_num,
                    parsed["sku"],
                    "; ".join(
                        f"{field}: {', '.join(msgs)}"
                        for field, msgs in exc.message_dict.items()
                    ),
                )
                continue

            if product.pk is None:
                to_create.append(product)
            else:
                to_update.append(product)

        with transaction.atomic():
            if to_create:
                Product.objects.bulk_create(to_create, batch_size=CSV_BATCH_SIZE)
            if to_update:
                Product.objects.bulk_update(
                    to_update, PRODUCT_FIELDS, batch_size=CSV_BATCH_SIZE
                )

        counters["created"] += len(to_create)
        counters["updated"] += len(to_update)
        batch.clear()
        counters["rows"].clear()

    @staticmethod
    def import_products_from_csv(csv_file) -> Dict[str, Any]:
        stream = ProductService._open_csv_stream(csv_file)
        reader = csv.DictReader(stream)

        if reader.fieldnames is None:
            raise ValidationError("CSV file is empty")

        normalized_fields = {
            (f or "").strip().lower() for f in reader.fieldnames if f is not None
        }
        missing = {"name", "sku", "price", "stock"} - normalized_fields
        if missing:
            raise ValidationError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        field_mapping = {f.lower(): f for f in reader.fieldnames if f is not None}

        counters = {"created": 0, "updated": 0, "rows": []}
        errors: List[Dict[str, Any]] = []
        batch: List[Dict[str, Any]] = []
        seen_skus = set()
        row_count = 0

        for row_num, raw_row in enumerate(reader, start=2):
            row_count += 1
            row = {
                (k or "").lower().strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in raw_row.items()
            }

            try:
                parsed = ProductService._parse_csv_row(row, field_mapping, row_num)
            except ValidationError as exc:
                ProductService._record_error(errors, row_num, None, str(exc.message))
                continue
            except Exception as exc:
                ProductService._record_error(errors, row_num, None, str(exc))
                continue

            if parsed["sku"] in seen_skus:
                ProductService._flush_batch(batch, counters, errors)
                seen_skus.clear()

            seen_skus.add(parsed["sku"])
            batch.append(parsed)
            counters["rows"].append(row_num)

            if len(batch) >= CSV_BATCH_SIZE:
                ProductService._flush_batch(batch, counters, errors)
                seen_skus.clear()

        ProductService._flush_batch(batch, counters, errors)

        if row_count == 0:
            raise ValidationError("CSV file is empty")

        return {
            "created": counters["created"],
            "updated": counters["updated"],
            "errors": errors,
            "error_count": len(errors),
            "results": [],
            "total_processed": counters["created"] + counters["updated"] + len(errors),
        }

    @staticmethod
    def _record_error(errors, row_num, sku, message):
        if len(errors) < MAX_REPORTED_ERRORS:
            errors.append({"row": row_num, "sku": sku, "error": message})

    @staticmethod
    def _parse_csv_row(
        row: Dict[str, str], field_mapping: Dict[str, str], row_num: int
    ) -> Dict[str, Any]:
        def get_value(*possible_keys):
            for key in possible_keys:
                if key in row and row[key] not in ("", None):
                    return row[key]
                mapped_key = key.lower()
                if mapped_key in field_mapping:
                    original = field_mapping[mapped_key].lower().strip()
                    if original in row and row[original] not in ("", None):
                        return row[original]
            return None

        name = _sanitize_input_text(get_value("name"))
        sku = _sanitize_input_text(get_value("sku"))
        price_raw = get_value("price")
        stock_raw = get_value("stock")
        description = _sanitize_input_text(get_value("description") or "")
        category = get_value("category") or CategoryChoices.OTHER
        weight_raw = get_value("weight_kg", "weight", "weightkg")

        if not name or name.strip() == "":
            raise ValidationError(f"Missing name at row {row_num}")
        if not sku or sku.strip() == "":
            raise ValidationError(f"Missing sku at row {row_num}")

        price = _parse_price_value(price_raw, row_num)
        stock = _parse_stock_value(stock_raw, row_num)
        weight = _parse_weight_value(weight_raw)

        category_upper = str(category).upper().strip()
        valid_categories = [c[0] for c in CategoryChoices.choices]
        if category_upper not in valid_categories:
            category_upper = CategoryChoices.OTHER

        return {
            "name": name,
            "sku": sku,
            "description": description,
            "category": category_upper,
            "price": price,
            "stock": stock,
            "weight_kg": weight,
        }
