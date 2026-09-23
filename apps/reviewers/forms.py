from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from apps.accounts.models import User
from apps.campaigns.models import Category
from apps.geo.models import Country

from .models import ReviewerProfile


class ReviewerProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=60, widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=60, widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "+254712345678",
        }),
    )

    class Meta:
        model = ReviewerProfile
        fields = ["country", "date_of_birth", "bio", "preferred_categories"]
        widgets = {
            "country": forms.Select(attrs={"class": "form-select"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": 500}),
            "preferred_categories": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"},
            ),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["phone_number"].initial = user.phone_number
        self.fields["country"].queryset = Country.objects.filter(is_active=True)
        self.fields["preferred_categories"].queryset = Category.objects.filter(is_active=True)

    def clean_phone_number(self):
        phone = (self.cleaned_data.get("phone_number") or "").strip()
        if phone and User.objects.filter(phone_number=phone).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone or None

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.phone_number = self.cleaned_data["phone_number"]
        if commit:
            self.user.save(update_fields=["first_name", "last_name", "phone_number"])
            profile.save()
            profile.preferred_categories.set(self.cleaned_data["preferred_categories"])
        return profile


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})