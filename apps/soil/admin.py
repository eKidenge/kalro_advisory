from django.contrib import admin

from .models import SoilTest, NutrientProfile, MarketPrice, AgDataSyncLog


@admin.register(SoilTest)
class SoilTestAdmin(admin.ModelAdmin):
    list_display = (
        'sample_id', 'farm', 'sampled_on', 'lab',
        'ph', 'nitrogen_pct', 'phosphorus_ppm', 'potassium_ppm',
    )
    list_filter = ('lab', 'sampled_on', 'farm__county')
    search_fields = ('sample_id', 'farm__name', 'farm__farmer__full_name')
    date_hierarchy = 'sampled_on'
    autocomplete_fields = ('farm',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Sample', {
            'fields': ('farm', 'sample_id', 'sampled_on', 'lab', 'sampled_by'),
        }),
        ('Macronutrients', {
            'fields': ('ph', 'organic_carbon_pct', 'nitrogen_pct',
                       'phosphorus_ppm', 'potassium_ppm'),
        }),
        ('Secondary & micronutrients', {
            'fields': ('calcium_ppm', 'magnesium_ppm', 'sulfur_ppm',
                       'zinc_ppm', 'boron_ppm', 'iron_ppm'),
        }),
        ('Physical', {
            'fields': ('texture', 'bulk_density', 'moisture_pct', 'cec_meq'),
        }),
        ('Meta', {
            'fields': ('notes', 'raw_payload', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(NutrientProfile)
class NutrientProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'crop', 'soil_texture', 'ph_min', 'ph_max',
                    'n_min_pct', 'n_max_pct')
    list_filter = ('soil_texture', 'crop')
    search_fields = ('name', 'crop__name')


@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = (
        'commodity', 'commodity_label', 'county', 'market_name',
        'price_ksh', 'unit', 'observed_on', 'source',
    )
    list_filter = ('commodity', 'county', 'source', 'observed_on')
    search_fields = ('commodity_label', 'market_name')
    date_hierarchy = 'observed_on'
    autocomplete_fields = ('county',)


@admin.register(AgDataSyncLog)
class AgDataSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'triggered_by',
        'soil_records_fetched', 'price_records_fetched',
        'started_at', 'finished_at',
    )
    list_filter = ('status',)
    readonly_fields = (
        'triggered_by', 'status', 'started_at', 'finished_at',
        'soil_records_fetched', 'price_records_fetched', 'error_log',
    )
    date_hierarchy = 'started_at'

    def has_add_permission(self, request):
        return False