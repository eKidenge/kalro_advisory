from django.contrib import admin

from .models import (
    WeatherStation, WeatherRecord, Forecast, ClimateAlert, KAOPSyncLog,
)


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'source', 'county', 'sub_county',
                    'is_active', 'last_synced_at')
    list_filter = ('source', 'is_active', 'county')
    search_fields = ('code', 'name', 'sub_county')
    list_editable = ('is_active',)
    autocomplete_fields = ('county',)


@admin.register(WeatherRecord)
class WeatherRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'station', 'rainfall_mm', 'temp_min_c',
                    'temp_max_c', 'humidity_pct', 'quality')
    list_filter = ('quality', 'station__county', 'station')
    search_fields = ('station__code', 'station__name')
    date_hierarchy = 'date'
    autocomplete_fields = ('station',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ('station', 'horizon', 'issued_at', 'valid_from',
                    'valid_to', 'expected_rainfall_mm', 'probability_pct')
    list_filter = ('horizon', 'station__county', 'station')
    search_fields = ('station__code', 'station__name', 'summary')
    date_hierarchy = 'issued_at'
    autocomplete_fields = ('station',)


@admin.register(ClimateAlert)
class ClimateAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'severity', 'status',
                    'county', 'sub_county', 'issued_at', 'valid_until')
    list_filter = ('kind', 'severity', 'status', 'county')
    search_fields = ('title', 'description', 'sub_county')
    filter_horizontal = ('affected_farms',)
    date_hierarchy = 'issued_at'
    autocomplete_fields = ('county',)
    readonly_fields = ('issued_at', 'resolved_at')


@admin.register(KAOPSyncLog)
class KAOPSyncLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'triggered_by', 'records_fetched',
                    'records_created', 'records_updated',
                    'started_at', 'finished_at')
    list_filter = ('status',)
    readonly_fields = (
        'triggered_by', 'status', 'started_at', 'finished_at',
        'records_fetched', 'records_created', 'records_updated', 'error_log',
    )
    date_hierarchy = 'started_at'

    def has_add_permission(self, request):
        return False