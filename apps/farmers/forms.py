from django import forms

from .models import Farmer, Farm, County, FarmerImportBatch


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


class FarmerForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Farmer
        fields = (
            'national_id', 'full_name', 'gender', 'date_of_birth',
            'phone_number', 'alt_phone_number', 'email',
            'county', 'sub_county', 'ward', 'village',
            'total_land_size', 'land_size_unit', 'primary_enterprise',
            'registration_source', 'is_active', 'notes',
        )
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_field_agent and user.county:
            self.fields['county'].queryset = County.objects.filter(
                name__iexact=user.county,
            )
            self.fields['county'].widget.attrs['readonly'] = True


class FarmForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Farm
        fields = (
            'farmer', 'name', 'size', 'size_unit',
            'county', 'sub_county', 'ward',
            'gps_latitude', 'gps_longitude',
            'altitude_m', 'soil_type', 'irrigation_type', 'is_agripark_demo',
        )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_field_agent and user.county:
            self.fields['county'].queryset = County.objects.filter(
                name__iexact=user.county,
            )
            self.fields['farmer'].queryset = Farmer.objects.filter(
                county__name__iexact=user.county,
            )


class FarmerImportForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = FarmerImportBatch
        fields = ('file',)