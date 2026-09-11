from django import forms

from apps.farmers.models import County
from .models import (
    WeatherStation, WeatherRecord, Forecast, ClimateAlert,
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


class WeatherRecordForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = WeatherRecord
        fields = (
            'station', 'date',
            'rainfall_mm', 'temp_min_c', 'temp_max_c',
            'humidity_pct', 'wind_speed_ms', 'solar_rad_mj',
            'evapotranspiration_mm', 'quality',
        )
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_field_agent and user.county:
            self.fields['station'].queryset = WeatherStation.objects.filter(
                county__name__iexact=user.county,
            )


class WeatherStationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = WeatherStation
        fields = (
            'code', 'name', 'source', 'county', 'sub_county',
            'latitude', 'longitude', 'altitude_m', 'is_active', 'installed_at',
        )
        widgets = {'installed_at': forms.DateInput(attrs={'type': 'date'})}


class ClimateAlertForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ClimateAlert
        fields = (
            'kind', 'severity', 'status',
            'county', 'sub_county', 'affected_farms',
            'title', 'description', 'recommended_action',
            'valid_until',
        )
        widgets = {
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class ForecastFilterForm(BootstrapMixin, forms.Form):
    station = forms.ModelChoiceField(
        queryset=WeatherStation.objects.all(), required=False,
    )
    horizon = forms.ChoiceField(
        choices=[('', 'All')] + list(Forecast.Horizon.choices),
        required=False,
    )
    date_from = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'}),
    )