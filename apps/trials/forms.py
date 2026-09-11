from django import forms

from .models import (
    TrialSite, Trial, TrialTreatment, TrialResult, TrialImportBatch,
)


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
                field.widget.attrs.setdefault('rows', 3)
            else:
                field.widget.attrs['class'] = (css + ' form-control').strip()


class TrialForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Trial
        fields = (
            'code', 'title', 'objective',
            'site', 'county', 'crop', 'season',
            'status', 'design', 'replications',
            'lead_researcher', 'started_on', 'ended_on',
            'is_published', 'notes',
        )
        widgets = {
            'started_on': forms.DateInput(attrs={'type': 'date'}),
            'ended_on': forms.DateInput(attrs={'type': 'date'}),
        }


class TrialResultForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TrialResult
        fields = (
            'treatment', 'plot_number', 'replication', 'observed_on',
            'plant_height_cm', 'biomass_kg_ha',
            'grain_yield_kg_ha', 'total_yield_kg_ha',
            'soil_ph', 'soil_n_pct', 'soil_p_ppm', 'soil_k_ppm',
            'nitrogen_use_efficiency', 'rainfall_mm',
            'notes',
        )
        widgets = {'observed_on': forms.DateInput(attrs={'type': 'date'})}


class TrialImportForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TrialImportBatch
        fields = ('file', 'trial')