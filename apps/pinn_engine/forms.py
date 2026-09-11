from django import forms

from .models import (
    PhysicsConstraint, PINNModel, TrainingRun, InferenceRun, ModelMetric,
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


class PINNModelForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PINNModel
        fields = (
            'name', 'version', 'description',
            'architecture', 'hidden_layers', 'activation',
            'input_features', 'output_targets',
            'physics_constraints', 'physics_lambda',
            'status', 'artifact_path', 'metrics',
        )


class PhysicsConstraintForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PhysicsConstraint
        fields = (
            'name', 'kind', 'domain', 'description',
            'mathematical_form', 'weight', 'is_active', 'crop',
        )


class TrainingRunForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TrainingRun
        fields = (
            'model', 'run_label',
            'epochs', 'batch_size', 'learning_rate', 'train_split',
        )


class InferenceRunForm(BootstrapMixin, forms.ModelForm):
    override_payload = forms.JSONField(
        required=False,
        help_text="Optional JSON overrides for input payload.",
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    class Meta:
        model = InferenceRun
        fields = ('model', 'farm', 'crop')


class ModelMetricFilterForm(BootstrapMixin, forms.Form):
    model = forms.ModelChoiceField(
        queryset=PINNModel.objects.all(), required=False, label="Model",
    )
    training_run = forms.ModelChoiceField(
        queryset=TrainingRun.objects.all(), required=False, label="Training run",
    )