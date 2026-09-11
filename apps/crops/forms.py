from django import forms

from .models import Crop, CropCategory, GrowthStage, CropCalendar


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


class CropForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Crop
        fields = (
            'name', 'scientific_name', 'code', 'category',
            'season', 'growth_habit', 'is_active',
            'days_to_maturity', 'expected_yield_kg_ha',
            'optimal_ph_min', 'optimal_ph_max',
            'base_temp_c', 'max_temp_c',
            'water_requirement_mm',
            'n_requirement_kg_ha',
            'p_requirement_kg_ha',
            'k_requirement_kg_ha',
            'notes',
        )


class GrowthStageForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = GrowthStage
        fields = (
            'crop', 'name', 'order', 'start_day', 'end_day',
            'kc_coefficient', 'water_requirement_mm',
            'n_requirement_kg_ha', 'p_requirement_kg_ha', 'k_requirement_kg_ha',
            'critical_notes',
        )


class CropCalendarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CropCalendar
        fields = (
            'crop', 'county', 'aez',
            'planting_start_month', 'planting_end_month',
            'harvest_start_month', 'harvest_end_month',
            'expected_rainfall_mm', 'notes',
        )