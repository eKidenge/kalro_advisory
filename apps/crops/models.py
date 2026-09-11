from django.db import models
from django.urls import reverse


class CropCategory(models.Model):
    """Cereals, Legumes, Horticulture, Tubers, Cash crops, etc."""
    name = models.CharField(max_length=64, unique=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Crop categories'

    def __str__(self):
        return self.name


class Crop(models.Model):
    """A crop variety or generic crop used in advisories."""

    class Season(models.TextChoices):
        LONG_RAINS = 'LR', 'Long Rains (Mar–May)'
        SHORT_RAINS = 'SR', 'Short Rains (Oct–Dec)'
        BOTH = 'BOTH', 'Both seasons'
        DRY = 'DRY', 'Dry season / irrigated'
        PERENNIAL = 'PER', 'Perennial'

    class GrowthHabit(models.TextChoices):
        ANNUAL = 'ANN', 'Annual'
        BIENNIAL = 'BIE', 'Biennial'
        PERENNIAL = 'PER', 'Perennial'

    name = models.CharField(max_length=128, unique=True, db_index=True)
    scientific_name = models.CharField(max_length=128, blank=True)
    code = models.CharField(max_length=16, unique=True, null=True, blank=True)

    category = models.ForeignKey(
        CropCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='crops',
    )
    season = models.CharField(max_length=6, choices=Season.choices, default=Season.BOTH)
    growth_habit = models.CharField(
        max_length=4, choices=GrowthHabit.choices, default=GrowthHabit.ANNUAL,
    )

    # PINN physics parameters
    optimal_ph_min = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    optimal_ph_max = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    water_requirement_mm = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Seasonal crop water requirement (mm).",
    )
    n_requirement_kg_ha = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Nitrogen requirement kg/ha.",
    )
    p_requirement_kg_ha = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    k_requirement_kg_ha = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    base_temp_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Base temperature for growing degree day calculations.",
    )
    max_temp_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )

    days_to_maturity = models.PositiveSmallIntegerField(null=True, blank=True)
    expected_yield_kg_ha = models.PositiveIntegerField(null=True, blank=True)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['season']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('crops:crop_detail', args=[self.pk])


class GrowthStage(models.Model):
    """Phenological stage of a crop (for stage-aware advisories)."""

    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='growth_stages')
    name = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField(default=1)

    start_day = models.PositiveSmallIntegerField(help_text="Days after planting.")
    end_day = models.PositiveSmallIntegerField(help_text="Days after planting.")

    kc_coefficient = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        help_text="Crop coefficient for evapotranspiration (FAO-56).",
    )
    water_requirement_mm = models.PositiveIntegerField(null=True, blank=True)
    n_requirement_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    p_requirement_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    k_requirement_kg_ha = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    critical_notes = models.TextField(
        blank=True,
        help_text="Stage-specific warnings (e.g. water stress sensitive).",
    )

    class Meta:
        ordering = ['crop', 'order']
        unique_together = ('crop', 'name')
        indexes = [models.Index(fields=['crop', 'order'])]

    def __str__(self):
        return f"{self.crop.name} — {self.name} (Day {self.start_day}-{self.end_day})"


class CropCalendar(models.Model):
    """Planting windows per crop per county / agro-ecological zone."""

    class AEZ(models.TextChoices):
        HIGHLAND = 'HL', 'Highland'
        MIDLAND = 'ML', 'Midland'
        LOWLAND = 'LL', 'Lowland'
        ARID = 'ARID', 'Arid / Semi-arid'

    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='calendars')
    county = models.ForeignKey(
        'farmers.County', on_delete=models.CASCADE, related_name='crop_calendars',
        null=True, blank=True,
    )
    aez = models.CharField(max_length=4, choices=AEZ.choices, blank=True)

    planting_start_month = models.PositiveSmallIntegerField(help_text="1–12")
    planting_end_month = models.PositiveSmallIntegerField(help_text="1–12")
    harvest_start_month = models.PositiveSmallIntegerField(null=True, blank=True)
    harvest_end_month = models.PositiveSmallIntegerField(null=True, blank=True)

    expected_rainfall_mm = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['crop', 'county']
        indexes = [models.Index(fields=['crop', 'county'])]

    def __str__(self):
        loc = self.county.name if self.county else (self.aez or 'Any')
        return f"{self.crop.name} @ {loc} (plant M{self.planting_start_month}-M{self.planting_end_month})"