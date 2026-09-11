from django import forms

from .models import IntegrationConfig, SyncLog, WebhookEvent


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


class IntegrationConfigForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = IntegrationConfig
        fields = (
            'provider', 'display_name', 'direction',
            'base_url', 'auth_type',
            'api_key', 'api_secret',
            'username', 'password', 'bearer_token', 'oauth_token_url',
            'extra_headers', 'extra_config',
            'is_active', 'is_sandbox',
        )


class SyncTriggerForm(BootstrapMixin, forms.Form):
    provider = forms.ChoiceField(choices=IntegrationConfig.Provider.choices)
    operation = forms.ChoiceField(choices=SyncLog.Operation.choices)
    dry_run = forms.BooleanField(required=False, initial=False)