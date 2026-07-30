from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.products.models import Product

from .forms import CheckoutForm
from .models import Order
from .services import OrderService


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def checkout_modal(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = CheckoutForm(initial={"quantity": 1})
    return render(
        request,
        "orders/partials/checkout_modal.html",
        {"product": product, "form": form},
    )


@require_http_methods(["GET", "POST"])
def process_checkout(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "GET":
        form = CheckoutForm(initial={"quantity": 1})
        return render(
            request,
            "orders/partials/checkout_modal.html",
            {"product": product, "form": form},
        )

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "orders/partials/checkout_modal.html",
            {"product": product, "form": form, "errors": form.errors},
        )

    quantity = form.cleaned_data["quantity"]
    customer_name = form.cleaned_data["customer_name"]
    customer_email = form.cleaned_data["customer_email"]

    if quantity > product.stock:
        form.add_error("quantity", f"Only {product.stock} items available in stock")
        return render(
            request,
            "orders/partials/checkout_modal.html",
            {"product": product, "form": form},
        )

    try:
        order = OrderService.single_product_purchase(
            product_id=product.id,
            quantity=quantity,
            customer_info={
                "customer_name": customer_name,
                "customer_email": customer_email,
            },
        )
    except ValidationError as exc:
        messages.error(
            request, str(exc.message if hasattr(exc, "message") else str(exc))
        )
        return render(
            request,
            "orders/partials/checkout_modal.html",
            {
                "product": product,
                "form": form,
                "error_message": exc.message if hasattr(exc, "message") else str(exc),
            },
        )
    except Exception as exc:
        return render(
            request,
            "orders/partials/checkout_modal.html",
            {"product": product, "form": form, "error_message": str(exc)},
        )

    return render(
        request,
        "orders/partials/order_success.html",
        {"order": order, "product": product},
    )


def order_detail(request, transaction_id):
    order = get_object_or_404(Order, transaction_id=transaction_id)
    context = {"order": order}

    if _is_htmx(request):
        return render(request, "orders/partials/order_success.html", context)

    return render(request, "orders/detail.html", context)


def order_list(request):
    email = request.GET.get("email")
    orders = OrderService.list_orders(customer_email=email if email else None)
    return render(
        request, "orders/list.html", {"orders": orders, "filter_email": email}
    )
