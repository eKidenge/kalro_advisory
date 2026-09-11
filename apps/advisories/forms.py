from django import forms

from .models import Advisory, AdvisoryDelivery, AdvisoryFeedback


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = (css + ' form-select').strip()
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = (css + ' form-control').strip()
                field.widget.attrs.setdefault('rows', 4)
            else:
                field.widget.attrs['class'] = (css + ' form-control').strip()


class AdvisoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Advisory
        fields = (
            'farmer', 'farm', 'crop', 'growth_stage',
            'kind', 'priority', 'status', 'source',
            'title', 'body', 'short_message',
            'explanation',
            'valid_from', 'valid_until',
        )
        widgets = {
            'valid_from': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
        }


class AdvisoryFeedbackForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = AdvisoryFeedback
        fields = ('advisory', 'rating', 'outcome', 'comment')


class AdvisoryGenerateForm(BootstrapMixin, forms.Form):
    """Manual trigger: choose farm + crop, run PINN inference → advisory."""

    farm = forms.ModelChoiceField(queryset=None, required=True)
    crop = forms.ModelChoiceField(queryset=None, required=True)
    kind = forms.ChoiceField(choices=Advisory.Kind.choices, initial=Advisory.Kind.FERTILIZER)
    priority = forms.ChoiceField(choices=Advisory.Priority.choices, initial=Advisory.Priority.NORMAL)
    notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'rows': 3}),
        help_text="Optional context for the advisory generation task.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.farmers.models import Farm
        from apps.crops.models import Crop

        farm_qs = Farm.objects.select_related('farmer')
        if user and user.is_field_agent and user.county:
            farm_qs = farm_qs.filter(county__name__iexact=user.county)

        self.fields['farm'].queryset = farm_qs
        self.fields['crop'].queryset = Crop.objects.filter(is_active=True)


class AdvisoryBulkGenerateForm(BootstrapMixin, forms.Form):
    """Batch generation across a county / crop — KALRO admin only."""

    county = forms.ModelChoiceField(queryset=None, required=True)
    crop = forms.ModelChoiceField(queryset=None, required=True)
    kind = forms.ChoiceField(choices=Advisory.Kind.choices, initial=Advisory.Kind.FERTILIZER)
    priority = forms.ChoiceField(choices=Advisory.Priority.choices, initial=Advisory.Priority.NORMAL)
    max_farms = forms.IntegerField(min_value=1, max_value=10000, initial=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.farmers.models import County
        from apps.crops.models import Crop
        self.fields['county'].queryset = County.objects.all()
        self.fields['crop'].queryset = Crop.objects.filter(is_active=True)