from django.contrib import admin
from django.utils.html import format_html

from .models import County, Farmer, Farm, FarmerImportBatch


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_agripark', 'latitude', 'longitude')
    list_filter = ('is_agripark',)
    search_fields = ('name',)
    list_editable = ('is_agripark',)
    ordering = ('name',)


class FarmInline(admin.TabularInline):
    model = Farm
    extra = 0
    fields = (
        'name', 'size', 'size_unit', 'county',
        'irrigation_type', 'gps_latitude', 'gps_longitude',
        'is_agripark_demo',
    )
    show_change_link = True


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'national_id', 'phone_number',
        'county', 'sub_county', 'primary_enterprise',
        'farm_count', 'is_active',
    )
    list_filter = ('is_active', 'county', 'gender', 'primary_enterprise', 'registration_source')
    search_fields = ('full_name', 'national_id', 'phone_number', 'email')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    date_hierarchy = 'created_at'
    inlines = [FarmInline]

    fieldsets = (
        ('Identity', {
            'fields': ('user', 'national_id', 'full_name', 'gender', 'date_of_birth'),
        }),
        ('Contact', {
            'fields': ('phone_number', 'alt_phone_number', 'email'),
        }),
        ('Location', {
            'fields': ('county', 'sub_county', 'ward', 'village'),
        }),
        ('Farming profile', {
            'fields': ('total_land_size', 'land_size_unit', 'primary_enterprise'),
        }),
        ('Registration', {
            'fields': ('registration_source', 'registered_by', 'is_active', 'notes'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Farms')
    def farm_count(self, obj):
        return obj.farms.count()


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'farmer', 'size', 'size_unit',
        'county', 'irrigation_type', 'is_agripark_demo', 'has_gps',
    )
    list_filter = ('county', 'irrigation_type', 'is_agripark_demo', 'soil_type')
    search_fields = ('name', 'farmer__full_name', 'farmer__national_id')
    autocomplete_fields = ('farmer',)
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(boolean=True, description='GPS')
    def has_gps(self, obj):
        return bool(obj.gps_latitude and obj.gps_longitude)


@admin.register(FarmerImportBatch)
class FarmerImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'uploaded_by', 'status', 'total_rows',
        'imported_count', 'failed_count', 'created_at',
    )
    list_filter = ('status',)
    readonly_fields = (
        'uploaded_by', 'status', 'total_rows', 'imported_count',
        'failed_count', 'error_log', 'started_at', 'finished_at', 'created_at',
    )

    def has_add_permission(self, request):
        return False