from django.conf import settings
from django.db import models
from django.urls import reverse


class IntegrationConfig(models.Model):
    """
    Configuration for one external system (KAOP, AgData Hub, Selector, iShamba).
    One row per provider — managed from admin.
    """

    class Provider(models.TextChoices):
        KAOP = 'KAOP', 'KAOP (Weather)'
        AGDATA = 'AGDATA', 'AgData Hub (Soil & Market)'
        SELECTOR = 'SELECTOR', 'Selector Platform'
        ISHAMBA = 'ISHAMBA', 'iShamba SMS'
        KALRO_REGISTRY = 'REGISTRY', 'KALRO Farmer Registry'
        OTHER = 'OTHER', 'Other'

    class AuthType(models.TextChoices):
        NONE = 'NONE', 'None'
        API_KEY = 'APIKEY', 'API Key'
        BEARER = 'BEARER', 'Bearer Token'
        BASIC = 'BASIC', 'Basic Auth'
        OAUTH2 = 'OAUTH2', 'OAuth 2.0'

    class Direction(models.TextChoices):
        INBOUND = 'IN', 'Inbound (pull)'
        OUTBOUND = 'OUT', 'Outbound (push)'
        BIDIRECTIONAL = 'BOTH', 'Bidirectional'

    provider = models.CharField(max_length=10, choices=Provider.choices, unique=True)
    display_name = models.CharField(max_length=128, blank=True)
    direction = models.CharField(max_length=6, choices=Direction.choices, default=Direction.BIDIRECTIONAL)

    base_url = models.URLField(blank=True)
    auth_type = models.CharField(max_length=8, choices=AuthType.choices, default=AuthType.API_KEY)
    api_key = models.CharField(max_length=256, blank=True)
    api_secret = models.CharField(max_length=256, blank=True)
    username = models.CharField(max_length=128, blank=True)
    password = models.CharField(max_length=256, blank=True)
    bearer_token = models.TextField(blank=True)
    oauth_token_url = models.URLField(blank=True)

    extra_headers = models.JSONField(default=dict, blank=True)
    extra_config = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)

    last_check_at = models.DateTimeField(null=True, blank=True)
    last_ok_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['provider']
        verbose_name = 'Integration configuration'
        verbose_name_plural = 'Integration configurations'

    def __str__(self):
        return f"{self.get_provider_display()} [{'active' if self.is_active else 'inactive'}]"

    def get_absolute_url(self):
        return reverse('integrations:integrationconfig_list')

    @property
    def is_healthy(self):
        return bool(self.last_ok_at) and not self.last_error


class SyncLog(models.Model):
    """One row per sync attempt against any integration."""

    class Operation(models.TextChoices):
        PULL_WEATHER = 'PULL_WEATHER', 'Pull Weather (KAOP)'
        PULL_FORECAST = 'PULL_FORECAST', 'Pull Forecast (KAOP)'
        PULL_SOIL = 'PULL_SOIL', 'Pull Soil (AgData)'
        PULL_MARKET = 'PULL_MARKET', 'Pull Market Prices (AgData)'
        PULL_REGISTRY = 'PULL_REGISTRY', 'Pull Farmer Registry'
        PUSH_ADVISORY_SMS = 'PUSH_SMS', 'Push SMS (iShamba)'
        PUSH_ADVISORY_SELECTOR = 'PUSH_SELECTOR', 'Push to Selector'
        HEALTH_CHECK = 'HEALTH', 'Health Check'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'

    config = models.ForeignKey(
        IntegrationConfig, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sync_logs',
    )
    provider = models.CharField(max_length=10, choices=IntegrationConfig.Provider.choices)
    operation = models.CharField(max_length=20, choices=Operation.choices)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='integration_syncs',
    )

    request_payload = models.JSONField(default=dict, blank=True)
    response_summary = models.JSONField(default=dict, blank=True)
    response_snippet = models.TextField(blank=True)

    records_fetched = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    error_text = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['provider', 'operation']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} / {self.get_operation_display()} — {self.status}"

    def get_absolute_url(self):
        return reverse('integrations:synclog_detail', args=[self.pk])


class WebhookEvent(models.Model):
    """
    Inbound webhook event from any provider (e.g. delivery receipts
    from Selector or iShamba, alerts from KAOP).
    """

    class Status(models.TextChoices):
        RECEIVED = 'RECEIVED', 'Received'
        PROCESSED = 'PROCESSED', 'Processed'
        IGNORED = 'IGNORED', 'Ignored'
        FAILED = 'FAILED', 'Failed'

    provider = models.CharField(max_length=10, choices=IntegrationConfig.Provider.choices)
    event_type = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RECEIVED)

    external_id = models.CharField(max_length=128, blank=True, db_index=True)
    signature_verified = models.BooleanField(default=False)

    headers = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    remote_ip = models.GenericIPAddressField(null=True, blank=True)

    related_sync_log = models.ForeignKey(
        SyncLog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='webhook_events',
    )

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_text = models.TextField(blank=True)

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} / {self.event_type or 'event'} [{self.status}]"

    def get_absolute_url(self):
        return reverse('integrations:webhookevent_detail', args=[self.pk])