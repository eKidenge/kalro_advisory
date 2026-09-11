from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, OTPCode, LoginAudit


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'get_full_name', 'role',
        'county', 'sub_county', 'is_verified', 'is_staff', 'is_active',
    )
    list_filter = (
        'role', 'is_verified', 'is_staff', 'is_superuser', 'is_active',
        'county', 'preferred_language',
    )
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'phone_number', 'county',
    )
    ordering = ('-date_joined',)
    list_per_page = 50
    list_editable = ('role', 'is_verified')
    actions = ['verify_users', 'unverify_users']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('KALRO Profile', {
            'fields': (
                'role', 'phone_number', 'county', 'sub_county', 'ward',
                'is_verified', 'preferred_language',
            ),
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('KALRO Profile', {
            'fields': (
                'role', 'phone_number', 'county', 'sub_county', 'ward',
                'is_verified', 'preferred_language',
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.action(description="Mark selected users as verified")
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} user(s) verified.")

    @admin.action(description="Mark selected users as NOT verified")
    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} user(s) unverified.")


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'code', 'created_at', 'expires_at', 'used_at')
    list_filter = ('purpose', 'used_at')
    search_fields = ('user__username', 'user__phone_number', 'code')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ('user', 'username_attempted', 'successful', 'ip_address', 'timestamp')
    list_filter = ('successful', 'timestamp')
    search_fields = ('user__username', 'username_attempted', 'ip_address')
    readonly_fields = ('user', 'username_attempted', 'ip_address',
                       'user_agent', 'successful', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False