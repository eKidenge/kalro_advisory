from django.contrib import admin

from .models import CropCategory, Crop, GrowthStage, CropCalendar


@admin.register(CropCategory)
class CropCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'crop_count')
    search_fields = ('name',)

    @admin.display(description='Crops')
    def crop_count(self, obj):
        return obj.crops.count()


class GrowthStageInline(admin.TabularInline):
    model = GrowthStage
    extra = 0
    fields = (
        'order', 'name', 'start_day', 'end_day', 'kc_coefficient',
        'water_requirement_mm', 'n_requirement_kg_ha',
    )
    ordering = ('order',)


class CropCalendarInline(admin.TabularInline):
    model = CropCalendar
    extra = 0
    fields = (
        'county', 'aez', 'planting_start_month', 'planting_end_month',
        'harvest_start_month', 'harvest_end_month',
    )


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'category', 'season', 'growth_habit',
        'water_requirement_mm', 'days_to_maturity', 'is_active',
    )
    list_filter = ('category', 'season', 'growth_habit', 'is_active')
    search_fields = ('name', 'scientific_name', 'code')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [GrowthStageInline, CropCalendarInline]

    fieldsets = (
        ('Identity', {
            'fields': ('name', 'scientific_name', 'code', 'category',
                       'season', 'growth_habit', 'is_active'),
        }),
        ('Agronomy', {
            'fields': ('days_to_maturity', 'expected_yield_kg_ha',
                       'optimal_ph_min', 'optimal_ph_max',
                       'base_temp_c', 'max_temp_c'),
        }),
        ('PINN physics parameters', {
            'fields': ('water_requirement_mm',
                       'n_requirement_kg_ha',
                       'p_requirement_kg_ha',
                       'k_requirement_kg_ha'),
        }),
        ('Notes', {'fields': ('notes',)}),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(GrowthStage)
class GrowthStageAdmin(admin.ModelAdmin):
    list_display = (
        'crop', 'order', 'name', 'start_day', 'end_day',
        'kc_coefficient', 'water_requirement_mm',
    )
    list_filter = ('crop',)
    search_fields = ('crop__name', 'name')
    autocomplete_fields = ('crop',)
    ordering = ('crop', 'order')


@admin.register(CropCalendar)
class CropCalendarAdmin(admin.ModelAdmin):
    list_display = (
        'crop', 'county', 'aez',
        'planting_start_month', 'planting_end_month',
        'harvest_start_month', 'harvest_end_month',
    )
    list_filter = ('crop', 'county', 'aez')
    search_fields = ('crop__name', 'county__name')
    autocomplete_fields = ('crop', 'county')