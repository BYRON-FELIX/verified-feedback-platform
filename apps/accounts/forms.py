from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.geo.models import Country

from .models import User, UserRole


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "class": "form-control"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )


class BaseSignupForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = self.role
        if commit:
            user.save()
        return user


class ReviewerSignupForm(BaseSignupForm):
    role = UserRole.REVIEWER

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        help_text="Optional for now. Required before you can withdraw earnings.",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+254712345678",
        }),
    )
    country = forms.ModelChoiceField(
        queryset=Country.objects.none(),
        empty_label="Select your country",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Used to show relevant tasks and payment options.",
    )

    class Meta(BaseSignupForm.Meta):
        fields = ("first_name", "last_name", "email", "phone_number", "country")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].queryset = Country.objects.filter(is_active=True)

    def clean_phone_number(self):
        phone = (self.cleaned_data.get("phone_number") or "").strip()
        if phone and User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone or None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone_number = self.cleaned_data.get("phone_number")
        if commit:
            user.save()
        return user


class BusinessSignupForm(BaseSignupForm):
    role = UserRole.BUSINESS

    company_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta(BaseSignupForm.Meta):
        fields = ("first_name", "last_name", "email", "company_name")

    def save(self, commit=True):
        user = super().save(commit=commit)
        # Company record creation will happen in the businesses app in a later step.
        # For now, we just store the name on first_name/last_name + company_name is
        # available in cleaned_data for later use.
        return user