from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, View

from .forms import (
    LoginForm, UserRegisterForm, ProfileUpdateForm,
    UserAdminUpdateForm, UserFilterForm,
)
from .models import User, LoginAudit


# ==================================================================
# Auditing helper
# ==================================================================
def _record_login(request, user, successful: bool, username_attempted=''):
    try:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
        LoginAudit.objects.create(
            user=user if successful else None,
            username_attempted=username_attempted,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            successful=successful,
        )
    except Exception:
        pass  # audit must never break login


# ==================================================================
# LOGIN — role-aware redirect
# ==================================================================
class KalroLoginView(LoginView):
    """
    Login view that:
      - uses our Bootstrap form
      - audits success/failure
      - redirects to role-specific dashboard
      - honours ?next=... for /admin/ and other protected URLs
      - blocks users who self-registered privileged roles but aren't verified
    """
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        _record_login(self.request, user, successful=True, username_attempted=user.username)

        # Block unverified privileged users
        if user.requires_verification and not user.is_verified:
            logout(self.request)
            messages.warning(
                self.request,
                "Your account is awaiting KALRO verification. "
                "You'll be able to log in once an admin approves it.",
            )
            return redirect('accounts:login')

        messages.success(self.request, f"Welcome back, {user.get_full_name() or user.username}.")
        return response

    def form_invalid(self, form):
        _record_login(
            self.request, None,
            successful=False,
            username_attempted=form.data.get('username', ''),
        )
        messages.error(self.request, "Invalid credentials.")
        return super().form_invalid(form)

    def get_success_url(self):
        # Honour ?next=... if present (e.g. /admin/ → login → back to /admin/)
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        # Otherwise → role-specific dashboard
        user = self.request.user
        try:
            return reverse(user.role_dashboard_url_name)
        except Exception:
            return reverse('advisories:advisory_dashboard')


class KalroLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You have been logged out.")
        return super().dispatch(request, *args, **kwargs)


# ==================================================================
# PASSWORD RESET
# ==================================================================
class KalroPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class KalroPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class KalroPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class KalroPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


# ==================================================================
# REGISTER
# ==================================================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('advisories:advisory_dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # If verification required → don't log in, show pending screen
            if user.requires_verification and not user.is_verified:
                messages.info(
                    request,
                    "Registration received. A KALRO administrator will verify "
                    "your account shortly. You'll receive an SMS or email once approved.",
                )
                return redirect('accounts:login')

            # ---- Auto-create a Farmer profile for farmers ----
            if user.role == 'FARMER':
                from apps.farmers.models import Farmer, County

                county = None
                if user.county:
                    county = County.objects.filter(
                        name__iexact=user.county.strip()
                    ).first()

                placeholder_id = f"SELF-{user.pk:08d}"

                Farmer.objects.get_or_create(
                    user=user,
                    defaults={
                        'national_id': placeholder_id,
                        'full_name': user.get_full_name() or user.username,
                        'phone_number': user.phone_number or '',
                        'email': user.email or '',
                        'county': county,
                        'sub_county': user.sub_county or '',
                        'ward': user.ward or '',
                        'registration_source': 'SELF',
                        'registered_by': user,
                        'is_active': True,
                    },
                )

            # Farmer → log in immediately
            login(request, user)
            messages.success(request, "Welcome to KALRO Advisory.")
            return redirect(user.role_dashboard_url_name)
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

# ==================================================================
# PROFILE
# ==================================================================
@login_required
def profile_view(request):
    audits = LoginAudit.objects.filter(user=request.user)[:10]
    return render(request, 'accounts/profile.html', {
        'profile_user': request.user,
        'audits': audits,
    })


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


# ==================================================================
# PASSWORD CHANGE
# ==================================================================
@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep session
            messages.success(request, "Password changed successfully.")
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)

    # Apply Bootstrap classes manually
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'form_title': 'Change Password',
    })


# ==================================================================
# USER MANAGEMENT (KALRO staff only)
# ==================================================================
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_kalro_staff

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to view that page.")
        return redirect('advisories:advisory_dashboard')


class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 50
    ordering = ['-date_joined']

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        role = self.request.GET.get('role')
        verified = self.request.GET.get('verified')
        county = self.request.GET.get('county')

        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(phone_number__icontains=q)
            )
        if role:
            qs = qs.filter(role=role)
        if verified == '1':
            qs = qs.filter(is_verified=True)
        elif verified == '0':
            qs = qs.filter(is_verified=False)
        if county:
            qs = qs.filter(county__icontains=county)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = UserFilterForm(self.request.GET or None)
        ctx['roles'] = User.Role.choices
        ctx['total'] = self.get_queryset().count()
        ctx['pending_verification'] = User.objects.filter(
            is_verified=False,
            role__in=[
                User.Role.EXTENSION_OFFICER,
                User.Role.RESEARCHER,
                User.Role.KALRO_ADMIN,
            ],
        ).count()
        return ctx


class UserDetailView(StaffRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['audits'] = LoginAudit.objects.filter(user=self.object)[:20]
        ctx['is_admin_view'] = True
        return ctx


class UserAdminUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f"Edit user: {self.object.username}"
        ctx['is_admin_view'] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"User {self.object.username} updated.")
        return super().form_valid(form)


# ==================================================================
# VERIFY / UNVERIFY ACTIONS
# ==================================================================
class UserVerifyView(StaffRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        messages.success(request, f"{user.username} verified.")
        return redirect('accounts:user_list')


class UserUnverifyView(StaffRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_verified = False
        user.save(update_fields=['is_verified'])
        messages.warning(request, f"{user.username} unverified.")
        return redirect('accounts:user_list')


# ==================================================================
# ROLE DASHBOARD ROUTER (handy alias)
# ==================================================================
@login_required
def role_router_view(request):
    """Generic entry point — redirects to the user's role dashboard."""
    return redirect(request.user.role_dashboard_url_name)