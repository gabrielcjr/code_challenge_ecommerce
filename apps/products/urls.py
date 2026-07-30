from django.urls import path

from . import views

urlpatterns = [
    path("", views.product_list, name="product-list"),
    path("search/", views.product_search, name="product-search"),
    path("products/<int:pk>/", views.product_detail, name="product-detail"),
    path(
        "products/create/modal/",
        views.product_create_modal,
        name="product-create-modal",
    ),
    path("products/create/", views.product_create, name="product-create"),
    path(
        "products/<int:pk>/edit/modal/",
        views.product_edit_modal,
        name="product-edit-modal",
    ),
    path("products/<int:pk>/edit/", views.product_update, name="product-update"),
    path("products/<int:pk>/delete/", views.product_delete, name="product-delete"),
    path("products/import/modal/", views.csv_import_modal, name="csv-import-modal"),
    path("products/import/", views.csv_import, name="csv-import"),
    path(
        "products/import/errors/download/",
        views.csv_import_error_report,
        name="csv-import-error-report",
    ),
]
