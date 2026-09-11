from django import forms

from apps.farmers.models import County, Farm
from .models import SoilTest, NutrientProfile, MarketPrice


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


class SoilTestForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SoilTest
        fields = (
            'farm', 'sample_id', 'sampled_on', 'lab', 'sampled_by',
            'ph', 'organic_carbon_pct', 'nitrogen_pct',
            'phosphorus_ppm', 'potassium_ppm',
            'calcium_ppm', 'magnesium_ppm', 'sulfur_ppm',
            'zinc_ppm', 'boron_ppm', 'iron_ppm',
            'texture', 'bulk_density', 'moisture_pct', 'cec_meq',
            'notes',
        )
        widgets = {'sampled_on': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_field_agent and user.county:
            self.fields['farm'].queryset = Farm.objects.filter(
                county__name__iexact=user.county,
            )


class NutrientProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = NutrientProfile
        fields = (
            'name', 'crop', 'soil_texture',
            'ph_min', 'ph_max',
            'n_min_pct', 'n_max_pct',
            'p_min_ppm', 'p_max_ppm',
            'k_min_ppm', 'k_max_ppm',
            'notes',
        )


class MarketPriceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = MarketPrice
        fields = (
            'commodity', 'commodity_label',
            'county', 'market_name',
            'price_ksh', 'unit', 'observed_on', 'source',
        )
        widgets = {'observed_on': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_field_agent and user.county:
            self.fields['county'].queryset = County.objects.filter(
                name__iexact=user.county,
            )