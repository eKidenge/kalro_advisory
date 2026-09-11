from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.farmers.models import County, Farm


class TrialSite(models.Model):
    """Physical location where a fertilizer / agronomy trial is run."""

    class SiteType(models.TextChoices):
        KALRO_CENTER = 'KALRO', 'KALRO Research Center'
        AGRIPARK = 'AGRIPARK', 'AgriPark'
        FARMER_FIELD = 'FARMER', "Farmer's Field"
        SCHOOL = 'SCHOOL', 'School / Institution'
        OTHER = 'OTHER', 'Other'

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    site_type = models.CharField(max_length=10, choices=SiteType.choices, default=SiteType.KALRO_CENTER)
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='trial_sites')
    sub_county = models.CharField(max_length=64, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    soil_type = models.CharField(max_length=64, blank=True)
    agro_ecological_zone = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['county', 'site_type'])]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def get_absolute_url(self):
        return reverse('trials:trial_site_detail', args=[self.pk])


class Trial(models.Model):
    """A single fertilizer / agronomy trial."""

    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        ONGOING = 'ONGOING', 'Ongoing'
        COMPLETED = 'DONE', 'Completed'
        SUSPENDED = 'SUSP', 'Suspended'
        ABANDONED = 'ABAND', 'Abandoned'

    class Design(models.TextChoices):
        RCBD = 'RCBD', 'Randomized Complete Block Design'
        CRD = 'CRD', 'Completely Randomized Design'
        SPLIT_PLOT = 'SPLIT', 'Split-plot'
        FACTORIAL = 'FACT', 'Factorial'
        DEMO = 'DEMO', 'Demonstration'
        OTHER = 'OTHER', 'Other'

    code = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    objective = models.TextField(blank=True)

    site = models.ForeignKey(TrialSite, on_delete=models.SET_NULL, null=True, related_name='trials')
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='trials')

    crop = models.ForeignKey(
        'crops.Crop', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='trials',
    )
    season = models.CharField(max_length=32, blank=True,
                              help_text="e.g. 2025 LR (Long Rains).")

    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PLANNED)
    design = models.CharField(max_length=6, choices=Design.choices, default=Design.RCBD)
    replications = models.PositiveSmallIntegerField(null=True, blank=True)

    lead_researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='led_trials',
    )
    started_on = models.DateField(null=True, blank=True, db_index=True)
    ended_on = models.DateField(null=True, blank=True)

    is_published = models.BooleanField(
        default=False,
        help_text="Published trials contribute to the 150K fertilizer database.",
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_on', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['crop', 'season']),
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"

    def get_absolute_url(self):
        return reverse('trials:trial_detail', args=[self.pk])

    @property
    def result_count(self):
        return self.results.count()


class TrialTreatment(models.Model):
    """A treatment arm within a trial (e.g. DAP 50kg/ha vs control)."""

    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name='treatments')
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    fertilizer_type = models.CharField(max_length=64, blank=True)
    n_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    p_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    k_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    organic_amendment = models.CharField(max_length=128, blank=True)

    is_control = models.BooleanField(default=False)

    class Meta:
        ordering = ['trial', 'code']
        unique_together = ('trial', 'code')

    def __str__(self):
        return f"{self.trial.code} / {self.code} — {self.name}"


class TrialResult(models.Model):
    """One observation per plot per treatment."""

    treatment = models.ForeignKey(TrialTreatment, on_delete=models.CASCADE, related_name='results')
    plot_number = models.CharField(max_length=16, blank=True)
    replication = models.PositiveSmallIntegerField(null=True, blank=True)

    observed_on = models.DateField(db_index=True)

    # Growth / yield
    plant_height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    biomass_kg_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grain_yield_kg_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_yield_kg_ha = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Soil / nutrient response
    soil_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    soil_n_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    soil_p_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    soil_k_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    # Agronomic efficiency
    nitrogen_use_efficiency = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    rainfall_mm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True)
    source_row = models.JSONField(null=True, blank=True,
                                  help_text="Original row from imported CSV.")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-observed_on']
        indexes = [
            models.Index(fields=['treatment', 'observed_on']),
            models.Index(fields=['observed_on']),
        ]

    def __str__(self):
        return f"{self.treatment} — {self.observed_on}"


class TrialImportBatch(models.Model):
    """Tracks CSV import batches (e.g. the 150K fertilizer trial DB)."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='trial_imports',
    )
    file = models.FileField(upload_to='trial_imports/%Y/%m/')
    trial = models.ForeignKey(
        Trial, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='import_batches',
        help_text="Optional — leave blank if the CSV specifies trial codes.",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Trial import #{self.pk} — {self.status}"