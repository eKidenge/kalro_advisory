from django.contrib import admin

from .models import (
    TrialSite, Trial, TrialTreatment, TrialResult, TrialImportBatch,
)


@admin.register(TrialSite)
class TrialSiteAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'site_type', 'county', 'sub_county', 'is_active')
    list_filter = ('site_type', 'is_active', 'county')
    search_fields = ('code', 'name', 'sub_county')
    list_editable = ('is_active',)
    autocomplete_fields = ('county',)


class TrialTreatmentInline(admin.TabularInline):
    model = TrialTreatment
    extra = 0
    fields = (
        'code', 'name', 'fertilizer_type',
        'n_kg_ha', 'p_kg_ha', 'k_kg_ha',
        'organic_amendment', 'is_control',
    )


@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'title', 'site', 'crop', 'season',
        'status', 'design', 'replications',
        'started_on', 'is_published', 'result_count',
    )
    list_filter = ('status', 'design', 'is_published', 'crop', 'county', 'season')
    search_fields = ('code', 'title', 'objective')
    date_hierarchy = 'started_on'
    autocomplete_fields = ('site', 'county', 'crop', 'lead_researcher')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TrialTreatmentInline]

    fieldsets = (
        ('Identity', {
            'fields': ('code', 'title', 'objective'),
        }),
        ('Location & crop', {
            'fields': ('site', 'county', 'crop', 'season'),
        }),
        ('Design', {
            'fields': ('status', 'design', 'replications'),
        }),
        ('People & dates', {
            'fields': ('lead_researcher', 'started_on', 'ended_on'),
        }),
        ('Publishing', {
            'fields': ('is_published', 'notes'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Results')
    def result_count(self, obj):
        return obj.results.count()


@admin.register(TrialTreatment)
class TrialTreatmentAdmin(admin.ModelAdmin):
    list_display = (
        'trial', 'code', 'name', 'fertilizer_type',
        'n_kg_ha', 'p_kg_ha', 'k_kg_ha', 'is_control',
    )
    list_filter = ('trial', 'is_control', 'fertilizer_type')
    search_fields = ('trial__code', 'code', 'name')
    autocomplete_fields = ('trial',)
    ordering = ('trial', 'code')


@admin.register(TrialResult)
class TrialResultAdmin(admin.ModelAdmin):
    list_display = (
        'treatment', 'plot_number', 'replication', 'observed_on',
        'grain_yield_kg_ha', 'biomass_kg_ha', 'rainfall_mm',
    )
    list_filter = ('observed_on', 'treatment__trial')
    search_fields = ('treatment__trial__code', 'treatment__code', 'plot_number')
    date_hierarchy = 'observed_on'
    autocomplete_fields = ('treatment',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Plot', {
            'fields': ('treatment', 'plot_number', 'replication', 'observed_on'),
        }),
        ('Growth & yield', {
            'fields': ('plant_height_cm', 'biomass_kg_ha',
                       'grain_yield_kg_ha', 'total_yield_kg_ha'),
        }),
        ('Soil response', {
            'fields': ('soil_ph', 'soil_n_pct', 'soil_p_ppm', 'soil_k_ppm'),
        }),
        ('Efficiency & environment', {
            'fields': ('nitrogen_use_efficiency', 'rainfall_mm'),
        }),
        ('Meta', {
            'fields': ('notes', 'source_row', 'created_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(TrialImportBatch)
class TrialImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'uploaded_by', 'trial', 'status',
        'total_rows', 'imported_count', 'failed_count', 'created_at',
    )
    list_filter = ('status',)
    readonly_fields = (
        'uploaded_by', 'status', 'total_rows', 'imported_count',
        'failed_count', 'error_log', 'started_at', 'finished_at', 'created_at',
    )

    def has_add_permission(self, request):
        return False