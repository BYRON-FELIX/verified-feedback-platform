from django import forms
from django.forms import inlineformset_factory

from .models import (
    Campaign,
    CampaignQuestion,
    CampaignRequirement,
)


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            "title", "category", "campaign_type", "description", "instructions",
            "reward_amount", "target_participants",
            "start_date", "end_date",
            "county", "location_description",
            "estimated_minutes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "campaign_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "reward_amount": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.01", "placeholder": "2.00",
            }),
            "target_participants": forms.NumberInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "county": forms.Select(attrs={"class": "form-select"}),
            "location_description": forms.TextInput(attrs={"class": "form-control"}),
            "estimated_minutes": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date must be on or after start date.")
        return cleaned


RequirementFormSet = inlineformset_factory(
    Campaign,
    CampaignRequirement,
    fields=("text", "is_mandatory", "order"),
    extra=3,
    can_delete=True,
    widgets={
        "text": forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Must have stayed at the property within the last 30 days",
        }),
        "is_mandatory": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "order": forms.NumberInput(attrs={"class": "form-control", "style": "width:80px"}),
    },
)


QuestionFormSet = inlineformset_factory(
    Campaign,
    CampaignQuestion,
    fields=("text", "question_type", "options", "is_required", "order"),
    extra=3,
    can_delete=True,
    widgets={
        "text": forms.TextInput(attrs={"class": "form-control"}),
        "question_type": forms.Select(attrs={"class": "form-select"}),
        "options": forms.Textarea(attrs={
            "class": "form-control", "rows": 2,
            "placeholder": "For choice types only. One option per line.",
        }),
        "is_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "order": forms.NumberInput(attrs={"class": "form-control", "style": "width:80px"}),
    },
)