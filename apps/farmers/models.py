from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class County(models.Model):
    """Kenyan counties — used for filtering farmers, farms, advisories."""
    name = models.CharField(max_length=64, unique=True, db_index=True)
    code = models.PositiveSmallIntegerField(unique=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_agripark = models.BooleanField(
        default=False,
        help_text="Whether KALRO operates an AgriPark in this county.",
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Counties'

    def __str__(self):
        return self.name


class Farmer(models.Model):
    """Farmer profile — one per registered user with role=FARMER."""

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    class FarmSizeUnit(models.TextChoices):
        ACRES = 'ACRE', 'Acres'
        HECTARES = 'HA', 'Hectares'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farmer_profile',
        null=True, blank=True,
    )
    national_id = models.CharField(max_length=20, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    alt_phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='farmers')
    sub_county = models.CharField(max_length=64, blank=True)
    ward = models.CharField(max_length=64, blank=True)
    village = models.CharField(max_length=64, blank=True)

    total_land_size = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    land_size_unit = models.CharField(
        max_length=6, choices=FarmSizeUnit.choices, default=FarmSizeUnit.ACRES,
    )
    primary_enterprise = models.CharField(
        max_length=64, blank=True,
        help_text="e.g. Maize, Dairy, Horticulture.",
    )

    registration_source = models.CharField(
        max_length=32, default='KALRO',
        help_text="KALRO, Extension Officer, Self, Bulk import, etc.",
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registered_farmers',
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['county', 'sub_county']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f"{self.full_name} — {self.county.name if self.county else 'Unknown'}"

    def get_absolute_url(self):
        return reverse('farmers:farmer_detail', args=[self.pk])


class Farm(models.Model):
    """A physical farm belonging to a farmer. A farmer can have many."""

    class IrrigationType(models.TextChoices):
        RAINFED = 'RAIN', 'Rain-fed'
        DRIP = 'DRIP', 'Drip'
        SPRINKLER = 'SPRINK', 'Sprinkler'
        FURROW = 'FURROW', 'Furrow'
        MIXED = 'MIXED', 'Mixed'
        NONE = 'NONE', 'None'

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='farms')
    name = models.CharField(max_length=128)
    size = models.DecimalField(max_digits=8, decimal_places=2)
    size_unit = models.CharField(
        max_length=6, choices=Farmer.FarmSizeUnit.choices, default=Farmer.FarmSizeUnit.ACRES,
    )

    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, related_name='farms')
    sub_county = models.CharField(max_length=64, blank=True)
    ward = models.CharField(max_length=64, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    soil_type = models.CharField(max_length=64, blank=True)
    irrigation_type = models.CharField(
        max_length=6, choices=IrrigationType.choices, default=IrrigationType.RAINFED,
    )
    is_agripark_demo = models.BooleanField(
        default=False,
        help_text="Farm used as an AgriPark demo site.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['farmer', 'name']
        indexes = [
            models.Index(fields=['farmer']),
            models.Index(fields=['county']),
        ]

    def __str__(self):
        return f"{self.name} ({self.farmer.full_name})"

    def get_absolute_url(self):
        return reverse('farmers:farm_detail', args=[self.pk])


class FarmerImportBatch(models.Model):
    """Tracks CSV bulk imports of farmers (KALRO registry sync)."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        PARTIAL = 'PARTIAL', 'Partially Succeeded'
        FAILED = 'FAILED', 'Failed'

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='farmer_imports',
    )
    file = models.FileField(upload_to='farmer_imports/%Y/%m/')
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
        return f"Import #{self.pk} — {self.status} ({self.imported_count}/{self.total_rows})"