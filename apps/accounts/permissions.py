"""
Shared role-based access control for the KALRO Advisory System.

Usage in any app:

    from apps.accounts.permissions import (
        KALROAdminRequired, KALROStaffRequired, ResearcherRequired,
        FieldOrAboveRequired, FarmerAccess, AnyAuthenticated,
    )

    class MyView(KALROStaffRequired, ListView):
        ...

Role matrix:
    FARMER           — own data only
    EXT_OFFICER      — county-scoped data
    RESEARCHER       — all data (read), some write
    KALRO_ADMIN      — all data + user management + integration configs
    SYS_ADMIN        — everything, including Django superuser
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base role gate. Subclass and set `allowed_roles`.
    Superusers always pass.
    """
    allowed_roles: set = set()
    redirect_url: str = 'advisories:advisory_dashboard'
    error_message: str = "You don't have permission to view that page."

    def test_func(self):
        u = self.request.user
        if not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        if not self.allowed_roles:
            return True
        return u.role in self.allowed_roles

    def handle_no_permission(self):
        messages.error(self.request, self.error_message)
        return redirect(self.redirect_url)

    # --- helpers used by list/detail views to scope querysets ---
    def scoped_county(self):
        """
        Return the county name this user is restricted to,
        or None if the user sees everything.
        """
        u = self.request.user
        if u.is_superuser or u.is_kalro_staff or u.is_researcher:
            return None
        if u.is_field_agent and u.county:
            return u.county
        return None

    def scope_queryset_by_county(self, qs, county_field='county'):
        """Apply county scoping if applicable."""
        county = self.scoped_county()
        if county:
            qs = qs.filter(**{f'{county_field}__name__iexact': county})
        return qs


# ==================================================================
# Pre-built role gates
# ==================================================================

class KALROAdminRequired(RoleRequiredMixin):
    """Only KALRO_ADMIN + SYS_ADMIN."""
    allowed_roles = {'KALRO_ADMIN', 'SYS_ADMIN'}
    error_message = "Only KALRO administrators can access this."


class KALROStaffRequired(RoleRequiredMixin):
    """Admins + extension officers + researchers."""
    allowed_roles = {'KALRO_ADMIN', 'SYS_ADMIN', 'EXT_OFFICER', 'RESEARCHER'}
    error_message = "KALRO staff access only."


class ResearcherRequired(RoleRequiredMixin):
    """Admins + researchers — no field agents."""
    allowed_roles = {'KALRO_ADMIN', 'SYS_ADMIN', 'RESEARCHER'}
    error_message = "Researcher or KALRO admin access only."


class FieldOrAboveRequired(RoleRequiredMixin):
    """Admins + extension officers — no researchers."""
    allowed_roles = {'KALRO_ADMIN', 'SYS_ADMIN', 'EXT_OFFICER'}
    error_message = "Field staff or above only."


class FarmerAccess(RoleRequiredMixin):
    """Any authenticated user (usually a farmer viewing own data)."""
    allowed_roles = set()

    def test_func(self):
        return self.request.user.is_authenticated


class AnyAuthenticated(RoleRequiredMixin):
    """Any logged-in user, no role restriction."""
    allowed_roles = set()

    def test_func(self):
        return self.request.user.is_authenticated


# ==================================================================
# Function-based-view decorators (mirrors of the mixins)
# ==================================================================
from functools import wraps
from django.contrib.auth.decorators import login_required


def role_required(*roles, redirect_to='advisories:advisory_dashboard',
                  error_message="You don't have permission to view that page."):
    """Decorator for function-based views."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            u = request.user
            if u.is_superuser or not roles or u.role in roles:
                return view(request, *args, **kwargs)
            messages.error(request, error_message)
            return redirect(redirect_to)
        return wrapper
    return decorator


def kalro_admin_required(view):
    return role_required('KALRO_ADMIN', 'SYS_ADMIN')(view)


def kalro_staff_required(view):
    return role_required('KALRO_ADMIN', 'SYS_ADMIN', 'EXT_OFFICER', 'RESEARCHER')(view)


def researcher_required(view):
    return role_required('KALRO_ADMIN', 'SYS_ADMIN', 'RESEARCHER')(view)


def field_or_above_required(view):
    return role_required('KALRO_ADMIN', 'SYS_ADMIN', 'EXT_OFFICER')(view)