from decimal import Decimal

from django import forms

from .models import CategoryChoices, Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "description",
            "category",
            "price",
            "stock",
            "weight_kg",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "Product name"}
            ),
            "sku": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "SKU-001"}
            ),
            "description": forms.Textarea(
                attrs={"class": "input-field", "rows": 3, "placeholder": "Description"}
            ),
            "category": forms.Select(attrs={"class": "input-field"}),
            "price": forms.NumberInput(
                attrs={"class": "input-field", "step": "0.01", "min": "0"}
            ),
            "stock": forms.NumberInput(
                attrs={"class": "input-field", "min": "0", "step": "1"}
            ),
            "weight_kg": forms.NumberInput(
                attrs={"class": "input-field", "step": "0.001", "min": "0"}
            ),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < Decimal("0"):
            raise forms.ValidationError("Price cannot be negative")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock cannot be negative")
        return stock


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text=(
            "Upload CSV with columns: name, sku, description, "
            "category, price, stock, weight_kg"
        ),
        widget=forms.FileInput(attrs={"class": "input-field", "accept": ".csv"}),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")
        if not csv_file:
            raise forms.ValidationError("No file provided")

        if not csv_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("File must be CSV format")

        if csv_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File size must be less than 5MB")

        return csv_file


class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "Search products...",
                "hx-get": "/search/",
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": "#product-table-container",
                "hx-indicator": "#search-indicator",
            }
        ),
    )
    category = forms.ChoiceField(
        required=False,
        choices=[("", "All Categories")] + list(CategoryChoices.choices),
        widget=forms.Select(attrs={"class": "input-field"}),
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "input-field", "placeholder": "Min price", "step": "0.01"}
        ),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "input-field", "placeholder": "Max price", "step": "0.01"}
        ),
    )
    in_stock = forms.ChoiceField(
        required=False,
        choices=[("", "All"), ("true", "In Stock"), ("false", "Out of Stock")],
        widget=forms.Select(attrs={"class": "input-field"}),
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ("-created_at", "Newest"),
            ("created_at", "Oldest"),
            ("name", "Name A-Z"),
            ("-name", "Name Z-A"),
            ("price", "Price Low-High"),
            ("-price", "Price High-Low"),
        ],
        widget=forms.Select(attrs={"class": "input-field"}),
    )
