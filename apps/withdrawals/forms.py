from django import forms


class WithdrawalRequestForm(forms.Form):
    amount_ksh = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=50,
        widget=forms.NumberInput(attrs={
            "class": "form-control", "step": "0.01", "placeholder": "100.00",
        }),
        label="Amount (KSh)",
    )
    destination_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "+254712345678",
        }),
        label="M-Pesa phone number",
    )