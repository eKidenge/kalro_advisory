from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, UserChangeForm, AuthenticationForm,
)

from .models import User


class BootstrapMixin:
    """Apply Bootstrap 5 classes to all form fields."""

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


class LoginForm(BootstrapMixin, AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Username or email'}),
    )
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegisterForm(BootstrapMixin, UserCreationForm):
    """
    Public self-registration.
    Farmers are auto-active. Other roles go to pending verification.
    """

    SELF_REGISTERABLE_ROLES = [
        (User.Role.FARMER, 'Farmer'),
        (User.Role.EXTENSION_OFFICER, 'Extension Officer (requires verification)'),
        (User.Role.RESEARCHER, 'Researcher (requires verification)'),
    ]

    role = forms.ChoiceField(
        choices=SELF_REGISTERABLE_ROLES,
        initial=User.Role.FARMER,
        help_text="Only Farmers get instant access. Other roles require KALRO verification.",
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the terms of use",
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'county', 'sub_county', 'ward',
            'role', 'preferred_language',
        )

    def clean_role(self):
        role = self.cleaned_data.get('role')
        allowed = {r[0] for r in self.SELF_REGISTERABLE_ROLES}
        if role not in allowed:
            raise forms.ValidationError("That role cannot be self-registered.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        # Farmers verified immediately; others wait for admin approval
        if user.role == User.Role.FARMER:
            user.is_verified = True
        else:
            user.is_verified = False
        if commit:
            user.save()
        return user


class UserAdminUpdateForm(BootstrapMixin, UserChangeForm):
    """Used by KALRO admins to edit any user."""

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'county', 'sub_county', 'ward',
            'role', 'preferred_language', 'is_verified', 'is_active',
        )


class ProfileUpdateForm(BootstrapMixin, forms.ModelForm):
    """Used by a user to edit their own profile (no role/verification)."""

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email',
            'phone_number', 'county', 'sub_county', 'ward',
            'preferred_language',
        )


class UserFilterForm(BootstrapMixin, forms.Form):
    """Search / filter form used in user_list.html."""

    q = forms.CharField(
        required=False, label="Search",
        widget=forms.TextInput(attrs={'placeholder': 'Name, email, phone…'}),
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All roles')] + list(User.Role.choices),
    )
    verified = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('1', 'Verified only'), ('0', 'Unverified only')],
    )
    county = forms.CharField(required=False, label="County")