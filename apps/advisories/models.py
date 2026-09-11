from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.farmers.models import Farmer, Farm
from apps.crops.models import Crop
from apps.pinn_engine.models import InferenceRun


class Advisory(models.Model):
    """A single advisory recommendation for a farmer / farm / crop."""

    class Kind(models.TextChoices):
        PLANTING = 'PLANTING', 'Planting'
        FERTILIZER = 'FERT', 'Fertilizer'
        IRRIGATION = 'IRRIG', 'Irrigation'
        PEST = 'PEST', 'Pest Management'
        DISEASE = 'DISEASE', 'Disease Management'
        WEATHER = 'WEATHER', 'Weather Warning'
        HARVEST = 'HARVEST', 'Harvest'
        MARKET = 'MARKET', 'Market'
        GENERAL = 'GEN', 'General'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCEL', 'Cancelled'

    class Source(models.TextChoices):
        PINN = 'PINN', 'PINN Engine'
        MANUAL = 'MANUAL', 'Manual'
        RULE = 'RULE', 'Rule-based'
        KALRO = 'KALRO', 'KALRO Bulletin'

    farmer = models.ForeignKey(
        Farmer, on_delete=models.CASCADE,
        related_name='advisories', null=True, blank=True,
    )
    farm = models.ForeignKey(
        Farm, on_delete=models.CASCADE,
        related_name='advisories', null=True, blank=True,
    )
    crop = models.ForeignKey(
        Crop, on_delete=models.SET_NULL,
        related_name='advisories', null=True, blank=True,
    )
    growth_stage = models.ForeignKey(
        'crops.GrowthStage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='advisories',
    )

    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.PINN)

    inference_run = models.ForeignKey(
        InferenceRun, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='advisories',
        help_text="The PINN inference that produced this advisory.",
    )

    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Farmer-facing message.")
    short_message = models.CharField(
        max_length=320, blank=True,
        help_text="SMS-friendly text (≤ 320 chars).",
    )

    # Explainability payload
    explanation = models.TextField(
        blank=True,
        help_text="Human-readable reasoning for the recommendation.",
    )
    explanation_factors = models.JSONField(
        default=list, blank=True,
        help_text="Ordered list of contributing factors, e.g. [{'name': 'rainfall', 'weight': 0.4}, ...]",
    )
    physics_residuals = models.JSONField(
        default=dict, blank=True,
        help_text="Copy of inference physics residuals for auditing.",
    )

    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='advisories_created',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='advisories_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['kind']),
            models.Index(fields=['farmer', 'created_at']),
            models.Index(fields=['farm', 'crop']),
        ]

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.title}"

    def get_absolute_url(self):
        return reverse('advisories:advisory_detail', args=[self.pk])

    @property
    def is_pending_approval(self):
        return self.status == self.Status.DRAFT

    @property
    def is_dispatchable(self):
        return self.status in {self.Status.APPROVED, self.Status.SENT}


class AdvisoryDelivery(models.Model):
    """Delivery log — one row per channel attempt."""

    class Channel(models.TextChoices):
        SMS = 'SMS', 'iShamba SMS'
        SELECTOR = 'SELECTOR', 'Selector Platform'
        EMAIL = 'EMAIL', 'Email'
        USSD = 'USSD', 'USSD'
        MANUAL = 'MANUAL', 'Manual / Verbal'

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        BOUNCED = 'BOUNCED', 'Bounced'

    advisory = models.ForeignKey(
        Advisory, on_delete=models.CASCADE, related_name='deliveries',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)

    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_ref = models.CharField(max_length=128, blank=True,
                                     help_text="Selector ID / email / etc.")

    provider_message_id = models.CharField(max_length=128, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_text = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['advisory', 'channel']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.advisory_id} → {self.get_channel_display()} [{self.status}]"


class AdvisoryFeedback(models.Model):
    """Farmer / extension officer feedback for closing the loop."""

    class Rating(models.TextChoices):
        VERY_POOR = '1', 'Very Poor'
        POOR = '2', 'Poor'
        NEUTRAL = '3', 'Neutral'
        GOOD = '4', 'Good'
        VERY_GOOD = '5', 'Very Good'

    class Outcome(models.TextChoices):
        FOLLOWED = 'FOLLOWED', 'Followed advice'
        PARTIAL = 'PARTIAL', 'Partially followed'
        NOT_FOLLOWED = 'NOT', 'Did not follow'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    advisory = models.ForeignKey(
        Advisory, on_delete=models.CASCADE, related_name='feedback',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='advisory_feedback',
    )
    rating = models.CharField(max_length=2, choices=Rating.choices, blank=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.UNKNOWN)
    comment = models.TextField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reported_at']
        indexes = [models.Index(fields=['advisory', 'rating'])]

    def __str__(self):
        return f"Feedback on advisory {self.advisory_id} — {self.get_rating_display() or 'N/A'}"