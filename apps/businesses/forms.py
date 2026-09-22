from django import forms

from .models import Business


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = [
            "name", "logo", "industry", "description",
            "registration_number", "kra_pin",
            "physical_address", "website",
            "support_email", "support_phone",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "industry": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Hospitality"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "registration_number": forms.TextInput(attrs={"class": "form-control"}),
            "kra_pin": forms.TextInput(attrs={"class": "form-control"}),
            "physical_address": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "support_email": forms.EmailInput(attrs={"class": "form-control"}),
            "support_phone": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and hasattr(logo, "size") and logo.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Logo must be under 2 MB.")
        return logo