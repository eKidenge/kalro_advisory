from django.contrib import admin

from .models import Advisory, AdvisoryDelivery, AdvisoryFeedback


class AdvisoryDeliveryInline(admin.TabularInline):
    model = AdvisoryDelivery
    extra = 0
    fields = (
        'channel', 'status', 'recipient_phone', 'recipient_ref',
        'provider_message_id', 'sent_at', 'delivered_at',
    )
    readonly_fields = ('sent_at', 'delivered_at')
    show_change_link = True


class AdvisoryFeedbackInline(admin.TabularInline):
    model = AdvisoryFeedback
    extra = 0
    fields = ('rating', 'outcome', 'reported_by', 'comment', 'reported_at')
    readonly_fields = ('reported_at',)


@admin.register(Advisory)
class AdvisoryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'kind', 'priority', 'status', 'source',
        'farmer', 'farm', 'crop', 'created_at',
    )
    list_filter = ('kind', 'priority', 'status', 'source', 'crop')
    search_fields = ('title', 'body', 'farmer__full_name', 'farm__name')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('farmer', 'farm', 'crop', 'growth_stage', 'inference_run')
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    inlines = [AdvisoryDeliveryInline, AdvisoryFeedbackInline]

    fieldsets = (
        ('Context', {
            'fields': ('farmer', 'farm', 'crop', 'growth_stage'),
        }),
        ('Classification', {
            'fields': ('kind', 'priority', 'status', 'source', 'inference_run'),
        }),
        ('Message', {
            'fields': ('title', 'body', 'short_message'),
        }),
        ('Explainability', {
            'fields': ('explanation', 'explanation_factors', 'physics_residuals'),
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until'),
        }),
        ('Approval', {
            'fields': ('created_by', 'approved_by', 'approved_at'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AdvisoryDelivery)
class AdvisoryDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'advisory', 'channel', 'status',
        'recipient_phone', 'provider_message_id',
        'queued_at', 'sent_at', 'delivered_at',
    )
    list_filter = ('channel', 'status')
    search_fields = ('recipient_phone', 'recipient_ref', 'provider_message_id')
    autocomplete_fields = ('advisory',)
    readonly_fields = ('queued_at', 'sent_at', 'delivered_at')


@admin.register(AdvisoryFeedback)
class AdvisoryFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'advisory', 'rating', 'outcome', 'reported_by', 'reported_at',
    )
    list_filter = ('rating', 'outcome')
    search_fields = ('advisory__title', 'comment')
    autocomplete_fields = ('advisory',)
    readonly_fields = ('reported_at',)