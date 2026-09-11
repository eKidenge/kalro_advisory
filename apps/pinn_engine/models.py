from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.farmers.models import Farm
from apps.crops.models import Crop


class PhysicsConstraint(models.Model):
    """
    A single physical law or empirical constraint embedded in the PINN loss.
    e.g. water balance: dS/dt = P - ET - R - D
    """

    class Kind(models.TextChoices):
        WATER_BALANCE = 'WATER', 'Water Balance'
        NUTRIENT_CYCLE = 'NUTRIENT', 'Nutrient Cycling'
        ENERGY_CONSERVATION = 'ENERGY', 'Energy Conservation'
        CARBON = 'CARBON', 'Carbon Balance'
        MASS = 'MASS', 'Mass Conservation'
        CUSTOM = 'CUSTOM', 'Custom'

    class Domain(models.TextChoices):
        SOIL = 'SOIL', 'Soil'
        PLANT = 'PLANT', 'Plant'
        ATMOSPHERE = 'ATM', 'Atmosphere'
        COMBINED = 'COMB', 'Combined'

    name = models.CharField(max_length=128, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    domain = models.CharField(max_length=6, choices=Domain.choices, default=Domain.COMBINED)
    description = models.TextField()
    mathematical_form = models.TextField(
        help_text="LaTeX or plain equation, e.g. dS/dt = P - ET - R - D",
    )

    weight = models.DecimalField(
        max_digits=6, decimal_places=4, default=1.0000,
        help_text="Weight in the composite loss: L = L_data + λ * L_physics.",
    )
    is_active = models.BooleanField(default=True)

    # Optional scoping
    crop = models.ForeignKey(
        Crop, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='physics_constraints',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['kind', 'name']
        indexes = [models.Index(fields=['kind', 'is_active'])]

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.name} (λ={self.weight})"

    def get_absolute_url(self):
        return reverse('pinn_engine:physics_constraint_list')


class PINNModel(models.Model):
    """A configured PINN — architecture + physics + artifact path."""

    class Architecture(models.TextChoices):
        MLP = 'MLP', 'Feed-forward MLP'
        LSTM = 'LSTM', 'LSTM'
        GRU = 'GRU', 'GRU'
        TRANSFORMER = 'TF', 'Transformer'
        HYBRID = 'HYBRID', 'Hybrid'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        TRAINING = 'TRAINING', 'Training'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    name = models.CharField(max_length=128, unique=True, db_index=True)
    version = models.CharField(max_length=32, default='0.1.0')
    description = models.TextField(blank=True)

    architecture = models.CharField(
        max_length=10, choices=Architecture.choices, default=Architecture.MLP,
    )
    hidden_layers = models.JSONField(
        default=list, blank=True,
        help_text="e.g. [64, 64, 32]",
    )
    activation = models.CharField(max_length=16, default='tanh')
    input_features = models.JSONField(
        default=list, blank=True,
        help_text="Ordered list of input feature names.",
    )
    output_targets = models.JSONField(
        default=list, blank=True,
        help_text="Ordered list of output targets (e.g. yield, N_uptake).",
    )

    physics_constraints = models.ManyToManyField(
        PhysicsConstraint, blank=True, related_name='models',
    )
    physics_lambda = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.1000,
        help_text="Global weight on the physics loss term.",
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    artifact_path = models.CharField(
        max_length=512, blank=True,
        help_text="Path to saved weights file (.pt / .h5).",
    )
    metrics = models.JSONField(
        default=dict, blank=True,
        help_text="Final metrics: rmse, r2, mae, physics_residual.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pinn_models',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"{self.name} v{self.version} [{self.status}]"

    def get_absolute_url(self):
        return reverse('pinn_engine:model_detail', args=[self.pk])


class TrainingRun(models.Model):
    """One training execution of a PINNModel."""

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        RUNNING = 'RUNNING', 'Running'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    model = models.ForeignKey(PINNModel, on_delete=models.CASCADE, related_name='training_runs')
    run_label = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)

    epochs = models.PositiveIntegerField(default=100)
    batch_size = models.PositiveIntegerField(default=64)
    learning_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0.001)
    train_split = models.DecimalField(max_digits=4, decimal_places=2, default=0.80)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Loss history (list of dicts)
    loss_history = models.JSONField(default=list, blank=True)
    final_metrics = models.JSONField(default=dict, blank=True)
    log_text = models.TextField(blank=True)
    error_text = models.TextField(blank=True)

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pinn_training_runs',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['model', 'status'])]

    def __str__(self):
        return f"{self.model.name} — {self.run_label or self.pk} [{self.status}]"

    def get_absolute_url(self):
        return reverse('pinn_engine:trainingrun_detail', args=[self.pk])


class InferenceRun(models.Model):
    """A single inference call — produces an advisory input payload."""

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'

    model = models.ForeignKey(PINNModel, on_delete=models.SET_NULL, null=True, related_name='inference_runs')
    training_run = models.ForeignKey(
        TrainingRun, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inferences',
    )
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True, related_name='inference_runs')
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name='inference_runs')

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)

    # Explainability
    feature_attributions = models.JSONField(
        default=dict, blank=True,
        help_text="e.g. {'rainfall': 0.42, 'soil_n': 0.31, ...}",
    )
    physics_residuals = models.JSONField(
        default=dict, blank=True,
        help_text="Residual per physics constraint — small = physically consistent.",
    )

    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_text = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pinn_inferences',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model', 'status']),
            models.Index(fields=['farm', 'crop']),
        ]

    def __str__(self):
        return f"Inference {self.pk} — {self.model.name if self.model else 'N/A'} [{self.status}]"

    def get_absolute_url(self):
        return reverse('pinn_engine:inference_detail', args=[self.pk])

    @property
    def total_physics_residual(self):
        if not self.physics_residuals:
            return None
        return sum(abs(v) for v in self.physics_residuals.values() if isinstance(v, (int, float)))


class ModelMetric(models.Model):
    """Point-in-time metric snapshot for dashboards (loss curves, RMSE, R²)."""

    model = models.ForeignKey(PINNModel, on_delete=models.CASCADE, related_name='metric_snapshots')
    training_run = models.ForeignKey(
        TrainingRun, on_delete=models.CASCADE, null=True, blank=True,
        related_name='metric_snapshots',
    )
    epoch = models.PositiveIntegerField(null=True, blank=True)
    step = models.PositiveIntegerField(null=True, blank=True)

    data_loss = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    physics_loss = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    total_loss = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    rmse = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    mae = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    r2 = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    physics_residual = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['model', 'epoch'])]

    def __str__(self):
        return f"{self.model.name} @ epoch {self.epoch}"