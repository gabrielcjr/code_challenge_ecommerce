import csv
import io

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .forms import CSVImportForm, ProductForm, ProductSearchForm
from .models import Product
from .services import ProductService


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def product_list(request):
    form = ProductSearchForm(request.GET or None)
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    in_stock = request.GET.get("in_stock", "")
    sort_by = request.GET.get("sort_by", "-created_at")
    page = request.GET.get("page", 1)

    result = ProductService.list_products(
        query=query or None,
        category=category or None,
        min_price=min_price or None,
        max_price=max_price or None,
        in_stock=in_stock or None,
        sort_by=sort_by,
        page=page,
    )

    context = {
        "products": result["products"],
        "page_obj": result["page_obj"],
        "paginator": result["paginator"],
        "total": result["total"],
        "search_form": form,
        "query": query,
        "category": category,
        "min_price": min_price,
        "max_price": max_price,
        "in_stock": in_stock,
        "sort_by": sort_by,
    }

    if (
        _is_htmx(request)
        and request.GET.get("q") is not None
        or request.headers.get("HX-Target") == "product-table-container"
    ):
        return render(request, "products/partials/product_table.html", context)

    if _is_htmx(request):
        target = request.headers.get("HX-Target", "")
        if target in ["product-table-container", "product-grid"]:
            return render(request, "products/partials/product_table.html", context)

    return render(request, "products/list.html", context)


def product_search(request):
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    in_stock = request.GET.get("in_stock", "")
    sort_by = request.GET.get("sort_by", "-created_at")
    page = request.GET.get("page", 1)

    result = ProductService.list_products(
        query=query or None,
        category=category or None,
        min_price=min_price or None,
        max_price=max_price or None,
        in_stock=in_stock or None,
        sort_by=sort_by,
        page=page,
    )

    context = {
        "products": result["products"],
        "page_obj": result["page_obj"],
        "paginator": result["paginator"],
        "total": result["total"],
        "query": query,
    }

    return render(request, "products/partials/product_table.html", context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {"product": product}

    if _is_htmx(request):
        return render(request, "products/partials/product_detail_modal.html", context)

    return render(request, "products/detail.html", context)


def product_create_modal(request):
    form = ProductForm()
    context = {"form": form, "action": "create", "title": "Create Product"}
    return render(request, "products/partials/product_form_modal.html", context)


@require_http_methods(["GET", "POST"])
def product_create(request):
    if request.method == "GET":
        form = ProductForm()
        context = {"form": form, "action": "create", "title": "Create Product"}
        return render(request, "products/partials/product_form_modal.html", context)

    form = ProductForm(request.POST)
    if form.is_valid():
        product = form.save()
        messages.success(request, f"Product {product.name} created successfully")

        result = ProductService.list_products(
            page=1, per_page=12, sort_by="-created_at"
        )
        context = {
            "products": result["products"],
            "page_obj": result["page_obj"],
            "paginator": result["paginator"],
            "total": result["total"],
        }

        if _is_htmx(request):
            response = render(request, "products/partials/product_table.html", context)
            response["HX-Trigger"] = "productCreated"
            response["HX-Retarget"] = "#product-table-container"
            return response

        return render(request, "products/list.html", context)

    context = {"form": form, "action": "create", "title": "Create Product"}

    if _is_htmx(request):
        return render(request, "products/partials/product_form_modal.html", context)

    return render(request, "products/form.html", context)


def product_edit_modal(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(instance=product)
    context = {
        "form": form,
        "product": product,
        "action": "edit",
        "title": f"Edit {product.name}",
    }
    return render(request, "products/partials/product_form_modal.html", context)


@require_http_methods(["GET", "POST"])
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "GET":
        form = ProductForm(instance=product)
        context = {
            "form": form,
            "product": product,
            "action": "edit",
            "title": f"Edit {product.name}",
        }
        return render(request, "products/partials/product_form_modal.html", context)

    form = ProductForm(request.POST, instance=product)
    if form.is_valid():
        updated = form.save()
        messages.success(request, f"Product {updated.name} updated successfully")

        result = ProductService.list_products(page=1, per_page=12)
        context = {
            "products": result["products"],
            "page_obj": result["page_obj"],
            "paginator": result["paginator"],
            "total": result["total"],
        }

        if _is_htmx(request):
            response = render(request, "products/partials/product_table.html", context)
            response["HX-Trigger"] = "productUpdated"
            return response

        return render(request, "products/list.html", context)

    context = {
        "form": form,
        "product": product,
        "action": "edit",
        "title": f"Edit {product.name}",
    }

    if _is_htmx(request):
        return render(request, "products/partials/product_form_modal.html", context)

    return render(request, "products/form.html", context)


@require_http_methods(["DELETE", "POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f"Product {product_name} deleted")

    result = ProductService.list_products(page=1, per_page=12)
    context = {
        "products": result["products"],
        "page_obj": result["page_obj"],
        "paginator": result["paginator"],
        "total": result["total"],
    }

    if _is_htmx(request):
        return render(request, "products/partials/product_table.html", context)

    return render(request, "products/list.html", context)


def csv_import_modal(request):
    form = CSVImportForm()
    return render(request, "products/partials/csv_import_modal.html", {"form": form})


@require_http_methods(["GET", "POST"])
def csv_import(request):
    if request.method == "GET":
        form = CSVImportForm()
        return render(
            request, "products/partials/csv_import_modal.html", {"form": form}
        )

    form = CSVImportForm(request.POST, request.FILES)
    if not form.is_valid():
        if _is_htmx(request):
            return render(
                request, "products/partials/csv_import_modal.html", {"form": form}
            )
        return render(request, "products/import.html", {"form": form})

    csv_file = form.cleaned_data["csv_file"]

    try:
        result = ProductService.import_products_from_csv(csv_file)
    except Exception as exc:
        form.add_error("csv_file", str(exc))
        if _is_htmx(request):
            return render(
                request, "products/partials/csv_import_modal.html", {"form": form}
            )
        return render(request, "products/import.html", {"form": form})

    request.session["last_import_errors"] = result.get("errors", [])
    request.session["last_import_summary"] = {
        "created": result.get("created", 0),
        "updated": result.get("updated", 0),
        "total_processed": result.get("total_processed", 0),
    }

    list_result = ProductService.list_products(page=1, per_page=12)
    context = {
        "import_result": result,
        "products": list_result["products"],
        "page_obj": list_result["page_obj"],
        "paginator": list_result["paginator"],
        "total": list_result["total"],
    }

    if _is_htmx(request):
        if result["errors"]:
            return render(request, "products/partials/csv_import_result.html", context)
        response = render(request, "products/partials/product_table.html", context)
        response["HX-Trigger"] = "csvImported"
        return response

    return render(request, "products/import_result.html", context)


def csv_import_error_report(request):
    errors = request.session.get("last_import_errors", [])

    if not errors:
        return HttpResponse("No import errors found", status=404)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row", "error", "sku", "name", "price", "stock", "raw_data"])

    for err in errors:
        data = err.get("data", {}) if isinstance(err.get("data"), dict) else {}
        writer.writerow(
            [
                err.get("row", ""),
                err.get("error", ""),
                data.get("sku", "") or data.get("SKU", ""),
                data.get("name", "") or data.get("Name", ""),
                data.get("price", "") or data.get("Price", ""),
                data.get("stock", "") or data.get("Stock", ""),
                str(data),
            ]
        )

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=import_errors_report.csv"
    return response
