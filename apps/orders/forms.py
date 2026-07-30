from django import forms


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=255,
        label="Full Name",
        widget=forms.TextInput(
            attrs={"class": "input-field", "placeholder": "John Doe", "required": True}
        ),
    )
    customer_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "john@example.com",
                "required": True,
            }
        ),
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Quantity",
        widget=forms.NumberInput(
            attrs={"class": "input-field", "min": "1", "step": "1"}
        ),
    )
    card_number = forms.CharField(
        max_length=19,
        label="Card Number",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "input-field", "placeholder": "4242 4242 4242 4242"}
        ),
    )
    card_expiry = forms.CharField(
        max_length=5,
        label="Expiry (MM/YY)",
        required=False,
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "12/30"}),
    )
    card_cvv = forms.CharField(
        max_length=4,
        label="CVV",
        required=False,
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "123"}),
    )

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be at least 1")
        return quantity
