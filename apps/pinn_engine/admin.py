from django.contrib import admin

from .models import (
    PhysicsConstraint, PINNModel, TrainingRun, InferenceRun, ModelMetric,
)


@admin.register(PhysicsConstraint)
class PhysicsConstraintAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'domain', 'weight', 'is_active', 'crop')
    list_filter = ('kind', 'domain', 'is_active', 'crop')
    search_fields = ('name', 'description', 'mathematical_form')
    list_editable = ('is_active', 'weight')


class ModelMetricInline(admin.TabularInline):
    model = ModelMetric
    extra = 0
    fields = ('epoch', 'data_loss', 'physics_loss', 'total_loss', 'rmse', 'r2')
    readonly_fields = ('epoch', 'data_loss', 'physics_loss', 'total_loss', 'rmse', 'r2')
    can_delete = False


@admin.register(PINNModel)
class PINNModelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'version', 'architecture', 'status',
        'physics_lambda', 'constraint_count', 'updated_at',
    )
    list_filter = ('status', 'architecture')
    search_fields = ('name', 'description')
    filter_horizontal = ('physics_constraints',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ModelMetricInline]

    fieldsets = (
        ('Identity', {'fields': ('name', 'version', 'description')}),
        ('Architecture', {
            'fields': ('architecture', 'hidden_layers', 'activation',
                       'input_features', 'output_targets'),
        }),
        ('Physics', {
            'fields': ('physics_constraints', 'physics_lambda'),
        }),
        ('State', {
            'fields': ('status', 'artifact_path', 'metrics'),
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Constraints')
    def constraint_count(self, obj):
        return obj.physics_constraints.count()


@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'model', 'run_label', 'status',
        'epochs', 'batch_size', 'learning_rate',
        'duration_seconds', 'started_at', 'finished_at',
    )
    list_filter = ('status', 'model')
    search_fields = ('model__name', 'run_label')
    readonly_fields = (
        'started_at', 'finished_at', 'duration_seconds',
        'loss_history', 'final_metrics', 'log_text', 'error_text',
    )
    autocomplete_fields = ('model',)
    date_hierarchy = 'created_at'


@admin.register(InferenceRun)
class InferenceRunAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'model', 'farm', 'crop', 'status',
        'duration_ms', 'requested_by', 'created_at',
    )
    list_filter = ('status', 'model')
    search_fields = ('farm__name', 'crop__name', 'requested_by__username')
    readonly_fields = (
        'input_payload', 'output_payload',
        'feature_attributions', 'physics_residuals',
        'duration_ms', 'error_text', 'created_at',
    )
    autocomplete_fields = ('model', 'farm', 'crop')
    date_hierarchy = 'created_at'


@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = (
        'model', 'training_run', 'epoch', 'step',
        'data_loss', 'physics_loss', 'total_loss',
        'rmse', 'r2', 'recorded_at',
    )
    list_filter = ('model', 'training_run')
    search_fields = ('model__name',)
    date_hierarchy = 'recorded_at'
    readonly_fields = ('recorded_at',)