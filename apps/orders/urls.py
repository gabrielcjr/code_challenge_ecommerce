from django.urls import path

from . import views

urlpatterns = [
    path("", views.order_list, name="order-list"),
    path(
        "checkout/<int:product_id>/modal/", views.checkout_modal, name="checkout-modal"
    ),
    path("checkout/<int:product_id>/", views.process_checkout, name="process-checkout"),
    path("<str:transaction_id>/", views.order_detail, name="order-detail"),
]
