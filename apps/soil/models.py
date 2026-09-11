from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.farmers.models import Farm, County


class SoilTest(models.Model):
    """A soil sample test result for a specific farm."""

    class Lab(models.TextChoices):
        KALRO = 'KALRO', 'KALRO'
        KEPHIS = 'KEPHIS', 'KEPHIS'
        PRIVATE = 'PRIVATE', 'Private Lab'
        FIELD_KIT = 'FIELD', 'Field Test Kit'
        OTHER = 'OTHER', 'Other'

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='soil_tests')
    sample_id = models.CharField(max_length=64, unique=True, db_index=True)
    sampled_on = models.DateField(db_index=True)
    lab = models.CharField(max_length=10, choices=Lab.choices, default=Lab.KALRO)
    sampled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='soil_samples',
    )

    # pH & macronutrients
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    organic_carbon_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    nitrogen_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    phosphorus_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    potassium_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    # Secondary & micronutrients
    calcium_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    magnesium_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    sulfur_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    zinc_ppm = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    boron_ppm = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    iron_ppm = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)

    # Physical
    texture = models.CharField(max_length=64, blank=True)
    bulk_density = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    moisture_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cec_meq = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                  help_text="Cation Exchange Capacity (meq/100g)")

    notes = models.TextField(blank=True)
    raw_payload = models.JSONField(null=True, blank=True,
                                   help_text="Original AgData Hub payload.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sampled_on']
        indexes = [
            models.Index(fields=['farm', 'sampled_on']),
            models.Index(fields=['sample_id']),
        ]

    def __str__(self):
        return f"{self.sample_id} — {self.farm.name}"

    def get_absolute_url(self):
        return reverse('soil:soiltest_detail', args=[self.pk])

    # --- simple interpretation helpers (used by templates + PINN) ---
    @property
    def ph_status(self):
        if self.ph is None:
            return 'unknown'
        ph = float(self.ph)
        if ph < 5.5:
            return 'acidic'
        if ph > 7.5:
            return 'alkaline'
        return 'optimal'

    @property
    def nitrogen_status(self):
        if self.nitrogen_pct is None:
            return 'unknown'
        n = float(self.nitrogen_pct)
        if n < 0.1:
            return 'low'
        if n > 0.3:
            return 'high'
        return 'adequate'


class NutrientProfile(models.Model):
    """
    Baseline / recommended nutrient ranges for a crop on a soil type.
    Consumed by the PINN nutrient-cycling constraint.
    """
    name = models.CharField(max_length=128)
    crop = models.ForeignKey('crops.Crop', on_delete=models.CASCADE,
                             related_name='nutrient_profiles', null=True, blank=True)
    soil_texture = models.CharField(max_length=64, blank=True)

    ph_min = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    ph_max = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    n_min_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    n_max_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    p_min_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    p_max_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    k_min_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    k_max_ppm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MarketPrice(models.Model):
    """Crop / input market prices (from AgData Hub)."""

    class Commodity(models.TextChoices):
        MAIZE = 'MAIZE', 'Maize'
        BEANS = 'BEANS', 'Beans'
        RICE = 'RICE', 'Rice'
        WHEAT = 'WHEAT', 'Wheat'
        SORGHUM = 'SORGHUM', 'Sorghum'
        MILlet = 'MILLET', 'Millet'
        POTATO = 'POTATO', 'Potato'
        TOMATO = 'TOMATO', 'Tomato'
        KALE = 'KALE', 'Kale'
        CABBAGE = 'CABBAGE', 'Cabbage'
        DAP = 'DAP', 'DAP Fertilizer'
        CAN = 'CAN', 'CAN Fertilizer'
        UREA = 'UREA', 'Urea'
        OTHER = 'OTHER', 'Other'

    commodity = models.CharField(max_length=10, choices=Commodity.choices, db_index=True)
    commodity_label = models.CharField(max_length=64, blank=True,
                                       help_text="Free-text if 'Other'.")
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True,
                               related_name='market_prices')
    market_name = models.CharField(max_length=128, blank=True)

    price_ksh = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=32, default='KES/kg')

    observed_on = models.DateField(db_index=True)
    source = models.CharField(max_length=32, default='AgData Hub')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-observed_on']
        indexes = [
            models.Index(fields=['commodity', 'observed_on']),
            models.Index(fields=['county', 'observed_on']),
        ]

    def __str__(self):
        return f"{self.get_commodity_display()} — KES {self.price_ksh} ({self.observed_on})"


class AgDataSyncLog(models.Model):
    """Tracks each AgData Hub pull (soil + market)."""

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'
        RUNNING = 'RUNNING', 'Running'

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agdata_syncs',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    soil_records_fetched = models.PositiveIntegerField(default=0)
    price_records_fetched = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"AgData sync {self.pk} — {self.status}"