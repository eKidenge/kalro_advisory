from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.farmers.models import County, Farm


class WeatherStation(models.Model):
    """KAOP weather station or virtual station keyed to a sub-county."""

    class Source(models.TextChoices):
        KAOP = 'KAOP', 'KAOP'
        MANUAL = 'MANUAL', 'Manual'
        SATELLITE = 'SAT', 'Satellite'
        OTHER = 'OTHER', 'Other'

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.KAOP)
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='weather_stations')
    sub_county = models.CharField(max_length=64, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    installed_at = models.DateField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['county'])]

    def __str__(self):
        return f"{self.name} ({self.code})"


class WeatherRecord(models.Model):
    """Daily weather observation — from KAOP or manual entry."""

    class Quality(models.TextChoices):
        RAW = 'RAW', 'Raw'
        QC_PASSED = 'QC', 'QC Passed'
        QC_FAILED = 'QCF', 'QC Failed'
        IMPUTED = 'IMP', 'Imputed'

    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='records')
    date = models.DateField(db_index=True)

    rainfall_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    temp_min_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temp_max_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    wind_speed_ms = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    solar_rad_mj = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    evapotranspiration_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    quality = models.CharField(max_length=4, choices=Quality.choices, default=Quality.RAW)
    source_payload = models.JSONField(null=True, blank=True, help_text="Raw KAOP payload for audit.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('station', 'date')
        indexes = [
            models.Index(fields=['station', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.station.code} — {self.date}"

    def get_absolute_url(self):
        return reverse('climate:weatherrecord_detail', args=[self.pk])


class Forecast(models.Model):
    """Forecast from KAOP or another provider."""

    class Horizon(models.TextChoices):
        D1 = 'D1', '1 day'
        D3 = 'D3', '3 days'
        D7 = 'D7', '7 days'
        D14 = 'D14', '14 days'
        SEASONAL = 'SEAS', 'Seasonal'

    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='forecasts')
    issued_at = models.DateTimeField(db_index=True)
    valid_from = models.DateField()
    valid_to = models.DateField()
    horizon = models.CharField(max_length=6, choices=Horizon.choices)

    expected_rainfall_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    expected_temp_min_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    expected_temp_max_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    probability_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['station', 'horizon']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]

    def __str__(self):
        return f"{self.station.code} — {self.horizon} @ {self.issued_at:%Y-%m-%d}"


class ClimateAlert(models.Model):
    """Drought, flood, or pest alerts derived from data + PINN."""

    class Kind(models.TextChoices):
        DROUGHT = 'DROUGHT', 'Drought'
        FLOOD = 'FLOOD', 'Flood'
        PEST = 'PEST', 'Pest Outbreak'
        HEAT = 'HEAT', 'Heat Stress'
        FROST = 'FROST', 'Frost'

    class Severity(models.TextChoices):
        INFO = 'INFO', 'Info'
        WATCH = 'WATCH', 'Watch'
        WARNING = 'WARN', 'Warning'
        EMERGENCY = 'EMERG', 'Emergency'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        RESOLVED = 'RESOLVED', 'Resolved'
        EXPIRED = 'EXPIRED', 'Expired'

    kind = models.CharField(max_length=8, choices=Kind.choices, db_index=True)
    severity = models.CharField(max_length=6, choices=Severity.choices, default=Severity.WATCH)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='climate_alerts')
    sub_county = models.CharField(max_length=64, blank=True)
    affected_farms = models.ManyToManyField(Farm, blank=True, related_name='climate_alerts')

    title = models.CharField(max_length=200)
    description = models.TextField()
    recommended_action = models.TextField(blank=True)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='climate_alerts_issued',
    )
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['kind', 'status']),
            models.Index(fields=['county']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.get_kind_display()} — {self.title}"


class KAOPSyncLog(models.Model):
    """Tracks each KAOP pull (weather + forecast)."""

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'
        RUNNING = 'RUNNING', 'Running'

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kaop_syncs',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    records_fetched = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"KAOP sync {self.pk} — {self.status}"