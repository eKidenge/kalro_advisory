from django.contrib import admin

from .models import IntegrationConfig, SyncLog, WebhookEvent


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = (
        'provider', 'display_name', 'direction',
        'auth_type', 'is_active', 'is_sandbox',
        'last_ok_at', 'last_check_at', 'is_healthy_flag',
    )
    list_filter = ('provider', 'auth_type', 'direction', 'is_active', 'is_sandbox')
    search_fields = ('display_name', 'base_url')
    list_editable = ('is_active', 'is_sandbox')
    readonly_fields = ('last_check_at', 'last_ok_at', 'last_error', 'created_at', 'updated_at')

    fieldsets = (
        ('Identity', {
            'fields': ('provider', 'display_name', 'direction'),
        }),
        ('Endpoint', {
            'fields': ('base_url', 'extra_headers', 'extra_config'),
        }),
        ('Authentication', {
            'fields': ('auth_type', 'api_key', 'api_secret',
                       'username', 'password', 'bearer_token', 'oauth_token_url'),
            'classes': ('collapse',),
        }),
        ('State', {
            'fields': ('is_active', 'is_sandbox',
                       'last_check_at', 'last_ok_at', 'last_error'),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(boolean=True, description='Healthy')
    def is_healthy_flag(self, obj):
        return obj.is_healthy


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'provider', 'operation', 'status',
        'records_fetched', 'records_created', 'records_updated', 'records_failed',
        'triggered_by', 'started_at', 'duration_ms',
    )
    list_filter = ('provider', 'operation', 'status')
    search_fields = ('error_text', 'response_snippet')
    date_hierarchy = 'started_at'
    autocomplete_fields = ('config',)
    readonly_fields = (
        'started_at', 'finished_at', 'duration_ms',
        'request_payload', 'response_summary', 'response_snippet', 'error_text',
    )


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'provider', 'event_type', 'status',
        'external_id', 'signature_verified',
        'remote_ip', 'received_at', 'processed_at',
    )
    list_filter = ('provider', 'event_type', 'status', 'signature_verified')
    search_fields = ('external_id', 'error_text')
    date_hierarchy = 'received_at'
    readonly_fields = (
        'provider', 'event_type', 'external_id', 'signature_verified',
        'headers', 'payload', 'remote_ip', 'related_sync_log',
        'received_at', 'processed_at', 'error_text',
    )

    def has_add_permission(self, request):
        return False