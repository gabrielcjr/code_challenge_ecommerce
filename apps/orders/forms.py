from django import forms

INPUT_CLASS = (
    "w-full rounded-lg border border-zinc-300 bg-white px-3.5 py-2.5 text-sm "
    "text-zinc-900 placeholder-zinc-400 shadow-sm focus:border-zinc-900 "
    "focus:ring-1 focus:ring-zinc-900 focus:outline-none transition"
)


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=255,
        label="Full Name",
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "John Doe", "required": True}
        ),
    )
    customer_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "john@example.com",
                "required": True,
            }
        ),
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Quantity",
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "min": "1", "step": "1"}),
    )
    card_number = forms.CharField(
        max_length=19,
        label="Card Number",
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "4242 4242 4242 4242"}
        ),
    )
    card_expiry = forms.CharField(
        max_length=5,
        label="Expiry (MM/YY)",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "12/30"}),
    )
    card_cvv = forms.CharField(
        max_length=4,
        label="CVV",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "123"}),
    )

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be at least 1")
        return quantity
