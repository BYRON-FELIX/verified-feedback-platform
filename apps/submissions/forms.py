from django import forms

from apps.campaigns.models import Campaign, CampaignQuestion, CampaignQuestionType


class DynamicQuestionForm(forms.Form):
    """
    Builds one form field per campaign question at __init__ time.
    Also includes overall rating, written feedback, and experience date.
    """

    overall_rating = forms.ChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Overall rating",
    )
    written_feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 5,
            "placeholder": "Tell us about your experience in your own words.",
        }),
        label="Written feedback",
    )
    experience_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date of experience",
    )

    def __init__(self, *args, campaign: Campaign, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = campaign

        for q in campaign.questions.all().order_by("order", "text"):
            field_name = f"q_{q.id}"
            field = self._build_field(q)
            self.fields[field_name] = field

    def _build_field(self, q: CampaignQuestion):
        required = q.is_required
        common_attrs = {"class": "form-control"}

        if q.question_type == CampaignQuestionType.TEXT:
            return forms.CharField(
                required=required, label=q.text,
                widget=forms.TextInput(attrs=common_attrs),
            )
        if q.question_type == CampaignQuestionType.LONG_TEXT:
            return forms.CharField(
                required=required, label=q.text,
                widget=forms.Textarea(attrs={**common_attrs, "rows": 4}),
            )
        if q.question_type == CampaignQuestionType.NUMBER:
            return forms.DecimalField(
                required=required, label=q.text,
                widget=forms.NumberInput(attrs=common_attrs),
            )
        if q.question_type == CampaignQuestionType.YES_NO:
            return forms.ChoiceField(
                required=required, label=q.text,
                choices=[("Yes", "Yes"), ("No", "No")],
                widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
            )
        if q.question_type == CampaignQuestionType.RATING:
            return forms.ChoiceField(
                required=required, label=q.text,
                choices=[(str(i), f"{i} ★") for i in range(1, 6)],
                widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
            )
        if q.question_type == CampaignQuestionType.SINGLE_CHOICE:
            choices = [(opt, opt) for opt in (q.options or [])]
            return forms.ChoiceField(
                required=required, label=q.text,
                choices=choices,
                widget=forms.Select(attrs={"class": "form-select"}),
            )
        if q.question_type == CampaignQuestionType.MULTI_CHOICE:
            choices = [(opt, opt) for opt in (q.options or [])]
            return forms.MultipleChoiceField(
                required=required, label=q.text,
                choices=choices,
                widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            )
        return forms.CharField(
            required=required, label=q.text,
            widget=forms.TextInput(attrs=common_attrs),
        )

    def question_fields(self):
        """Yield (question, bound_field) in order for template rendering."""
        for q in self.campaign.questions.all().order_by("order", "text"):
            yield q, self[f"q_{q.id}"]