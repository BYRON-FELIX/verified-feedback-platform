from django import forms

from .models import WithdrawalProvider


class WithdrawalRequestForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "step": "0.01", "placeholder": "100.00",
        }),
        label="Amount (USD)",
    )
    provider = forms.ChoiceField(
        choices=WithdrawalProvider.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Withdrawal method",
    )
    destination_phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "+254712345678",
        }),
        label="M-Pesa phone number (Kenya only)",
    )
    destination_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "form-control", "placeholder": "you@example.com",
        }),
        label="PayPal / card email (non-Kenya)",
    )