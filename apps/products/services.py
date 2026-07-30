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
    @transaction.atomic
    def import_products_from_csv(csv_file) -> Dict[str, Any]:
        content = csv_file.read().decode("utf-8")
        if not content.strip():
            raise ValidationError("CSV file is empty")

        reader = csv.DictReader(io.StringIO(content))
        required_fields = {"name", "sku", "price", "stock"}

        if reader.fieldnames is None:
            raise ValidationError("Invalid CSV format")

        normalized_fields = {f.strip().lower() for f in reader.fieldnames}
        missing = required_fields - normalized_fields
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        field_mapping = {f.lower(): f for f in reader.fieldnames}

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        created_count = 0
        updated_count = 0

        for row_num, raw_row in enumerate(reader, start=2):
            row = {
                k.lower().strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in raw_row.items()
            }

            try:
                parsed = ProductService._parse_csv_row(row, field_mapping, row_num)
            except ValidationError as exc:
                errors.append(
                    {"row": row_num, "data": raw_row, "error": str(exc.message)}
                )
                continue
            except Exception as exc:
                errors.append({"row": row_num, "data": raw_row, "error": str(exc)})
                continue

            sku = parsed["sku"]
            existing = Product.objects.filter(sku=sku).first()

            try:
                if existing:
                    for key, value in parsed.items():
                        setattr(existing, key, value)
                    existing.full_clean()
                    existing.save()
                    updated_count += 1
                    results.append({"row": row_num, "sku": sku, "action": "updated"})
                else:
                    product = Product(**parsed)
                    product.full_clean()
                    product.save()
                    created_count += 1
                    results.append({"row": row_num, "sku": sku, "action": "created"})
            except ValidationError as exc:
                errors.append(
                    {
                        "row": row_num,
                        "data": raw_row,
                        "error": "; ".join(
                            [
                                f"{k}: {', '.join(v)}"
                                for k, v in exc.message_dict.items()
                            ]
                        ),
                    }
                )
            except Exception as exc:
                errors.append({"row": row_num, "data": raw_row, "error": str(exc)})

        return {
            "created": created_count,
            "updated": updated_count,
            "errors": errors,
            "results": results,
            "total_processed": created_count + updated_count + len(errors),
        }

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
