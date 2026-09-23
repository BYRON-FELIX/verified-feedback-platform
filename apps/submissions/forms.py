from django import forms

from apps.campaigns.models import Campaign, CampaignQuestion, CampaignQuestionType


class DynamicQuestionForm(forms.Form):
    """
    Builds one form field per campaign question at __init__ time.
    Also includes overall rating and written feedback.
    """

    overall_rating = forms.ChoiceField(
        choices=[(i, f"{i} ★") for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={
            "class": "h-5 w-5 border-2 border-slate-300 text-emerald-700 focus:ring-2 focus:ring-emerald-200",
        }),
        label="Overall rating",
    )
    written_feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "block w-full rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-base text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100",
            "rows": 5,
            "placeholder": "Tell us about your experience in your own words.",
        }),
        label="Written feedback",
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
        common_attrs = {
            "class": "block w-full rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-base text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100",
        }

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
                widget=forms.RadioSelect(attrs={
                    "class": "h-5 w-5 border-2 border-slate-300 text-emerald-700 focus:ring-2 focus:ring-emerald-200",
                }),
            )
        if q.question_type == CampaignQuestionType.RATING:
            return forms.ChoiceField(
                required=required, label=q.text,
                choices=[(str(i), f"{i} ★") for i in range(1, 6)],
                widget=forms.RadioSelect(attrs={
                    "class": "h-5 w-5 border-2 border-slate-300 text-emerald-700 focus:ring-2 focus:ring-emerald-200",
                }),
            )
        if q.question_type == CampaignQuestionType.SINGLE_CHOICE:
            choices = [(opt, opt) for opt in (q.options or [])]
            return forms.ChoiceField(
                required=required, label=q.text,
                choices=choices,
                widget=forms.Select(attrs={
                    "class": "block w-full rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-base text-slate-900 shadow-sm outline-none transition focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100",
                }),
            )
        if q.question_type == CampaignQuestionType.MULTI_CHOICE:
            choices = [(opt, opt) for opt in (q.options or [])]
            return forms.MultipleChoiceField(
                required=required, label=q.text,
                choices=choices,
                widget=forms.CheckboxSelectMultiple(attrs={
                    "class": "h-5 w-5 rounded border-2 border-slate-300 text-emerald-700 focus:ring-2 focus:ring-emerald-200",
                }),
            )
        return forms.CharField(
            required=required, label=q.text,
            widget=forms.TextInput(attrs=common_attrs),
        )

    def question_fields(self):
        """Yield (question, bound_field) in order for template rendering."""
        for q in self.campaign.questions.all().order_by("order", "text"):
            yield q, self[f"q_{q.id}"]