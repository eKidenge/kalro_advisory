from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user for KALRO Advisory System.
    Roles drive what dashboards/actions a user can access.
    """

    class Role(models.TextChoices):
        FARMER = 'FARMER', 'Farmer'
        EXTENSION_OFFICER = 'EXT_OFFICER', 'Extension Officer'
        RESEARCHER = 'RESEARCHER', 'Researcher'
        KALRO_ADMIN = 'KALRO_ADMIN', 'KALRO Admin'
        SYSTEM_ADMIN = 'SYS_ADMIN', 'System Administrator'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FARMER,
        db_index=True,
        help_text="Determines dashboard & permissions.",
    )
    phone_number = models.CharField(
        max_length=20, blank=True, db_index=True,
        help_text="Used for iShamba SMS delivery.",
    )
    county = models.CharField(max_length=64, blank=True, db_index=True)
    sub_county = models.CharField(max_length=64, blank=True)
    ward = models.CharField(max_length=64, blank=True)

    is_verified = models.BooleanField(
        default=False,
        help_text="Verified by KALRO or an extension officer.",
    )
    preferred_language = models.CharField(
        max_length=10, default='en',
        choices=[('en', 'English'), ('sw', 'Kiswahili')],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['county', 'sub_county']),
        ]

    def __str__(self):
        full = self.get_full_name().strip()
        return f"{full or self.username} ({self.get_role_display()})"

    # --- role helpers ---
    @property
    def is_kalro_staff(self):
        return self.role in {self.Role.KALRO_ADMIN, self.Role.SYSTEM_ADMIN}

    @property
    def is_field_agent(self):
        return self.role == self.Role.EXTENSION_OFFICER

    @property
    def is_researcher(self):
        return self.role == self.Role.RESEARCHER

    @property
    def is_farmer(self):
        return self.role == self.Role.FARMER

    @property
    def requires_verification(self):
        """Only self-registered non-farmers need verification."""
        return self.role in {
            self.Role.EXTENSION_OFFICER,
            self.Role.RESEARCHER,
            self.Role.KALRO_ADMIN,
        }

    @property
    def role_dashboard_url_name(self):
        """Return the url name of the landing page for this user's role."""
        if self.is_farmer:
            return 'advisories:advisory_dashboard'
        if self.is_field_agent:
            return 'farmers:farmer_list'
        if self.is_researcher:
            return 'pinn_engine:metrics_dashboard'
        if self.is_kalro_staff:
            return 'advisories:advisory_dashboard'
        return 'advisories:advisory_dashboard'


class OTPCode(models.Model):
    """One-time code for phone verification / passwordless SMS login."""

    class Purpose(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        PHONE_VERIFY = 'PHONE_VERIFY', 'Phone Verification'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=8, db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'purpose', 'code'])]

    def __str__(self):
        return f"{self.user} – {self.purpose} – {self.code}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_expired and self.used_at is None


class LoginAudit(models.Model):
    """Tracks successful/failed logins for auditing."""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='login_audits',
    )
    username_attempted = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    successful = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['user', 'successful'])]

    def __str__(self):
        status = "OK" if self.successful else "FAIL"
        return f"[{status}] {self.username_attempted or self.user} @ {self.timestamp:%Y-%m-%d %H:%M}"