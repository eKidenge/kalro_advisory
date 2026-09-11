from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    KALROStaffRequired, KALROAdminRequired, FieldOrAboveRequired,
    researcher_required, kalro_admin_required, kalro_staff_required,
)
from apps.farmers.models import Farm, County
from apps.crops.models import Crop
from .forms import (
    AdvisoryForm, AdvisoryFeedbackForm,
    AdvisoryGenerateForm, AdvisoryBulkGenerateForm,
)
from .models import Advisory, AdvisoryDelivery, AdvisoryFeedback


# ==================================================================
# DASHBOARD — role-aware dispatcher
# ==================================================================
@login_required
def dashboard_view(request):
    user = request.user

    # ---- Pick template by role ----
    if user.is_farmer:
        template = 'advisories/dashboards/farmer_dashboard.html'
    elif user.is_field_agent:
        template = 'advisories/dashboards/extension_dashboard.html'
    elif user.is_researcher:
        template = 'advisories/dashboards/researcher_dashboard.html'
    elif user.is_kalro_staff or user.is_superuser:
        template = 'advisories/dashboards/admin_dashboard.html'
    else:
        template = 'advisories/dashboards/farmer_dashboard.html'

    # ---- Scoped queryset ----
    qs = Advisory.objects.all()
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        pass
    elif user.is_field_agent and user.county:
        qs = qs.filter(farm__county__name__iexact=user.county)
    elif user.is_farmer:
        qs = qs.filter(farmer__user=user)
    else:
        qs = qs.none()

    stats = {
        'total': qs.count(),
        'pending': qs.filter(status=Advisory.Status.DRAFT).count(),
        'approved': qs.filter(status=Advisory.Status.APPROVED).count(),
        'sent_today': qs.filter(
            status=Advisory.Status.SENT,
            created_at__date=timezone.now().date(),
        ).count(),
        'urgent': qs.filter(priority=Advisory.Priority.URGENT).count(),
        'by_kind': qs.values('kind').annotate(n=Count('id')).order_by('-n')[:8],
    }

    recent = qs.select_related('farmer', 'farm', 'crop')[:15]

    # ---- Admin-only extra context ----
    kpi = {}
    recent_logins = []
    integrations_status = []
    role_breakdown = []
    all_users = []
    all_farmers = []
    all_counties = []
    pending_advisories = []
    all_farms = []
    all_trials = []
    all_advisories = []
    all_pinn_models = []
    all_weather = []
    all_weather_stations = []
    all_soil_tests = []
    all_crops = []
    all_crop_categories = []
    all_integrations = []

    if user.is_kalro_staff or user.is_superuser:
        from apps.accounts.models import User, LoginAudit
        from apps.integrations.models import IntegrationConfig
        from apps.farmers.models import Farmer as FarmerModel, County as CountyModel
        from datetime import timedelta

        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        kpi = {
            'total_users': User.objects.count(),
            'pending_users': User.objects.filter(
                is_verified=False,
                role__in=['EXT_OFFICER', 'RESEARCHER', 'KALRO_ADMIN'],
            ).count(),
            'logins_today': LoginAudit.objects.filter(
                timestamp__date=today, successful=True,
            ).count(),
            'registrations_week': User.objects.filter(
                date_joined__gte=week_ago,
            ).count(),
            'failed_logins_today': LoginAudit.objects.filter(
                timestamp__date=today, successful=False,
            ).count(),
            'total_farmers': FarmerModel.objects.filter(is_active=True).count(),
            'total_integrations': IntegrationConfig.objects.count(),
            'total_counties': CountyModel.objects.count(),
        }

        # ---- Optional counts ----
        try:
            from apps.farmers.models import Farm as FarmModel
            kpi['total_farms'] = FarmModel.objects.count()
        except Exception:
            kpi['total_farms'] = 0

        try:
            from apps.climate.models import WeatherRecord
            kpi['total_weather'] = WeatherRecord.objects.count()
        except Exception:
            kpi['total_weather'] = 0

        try:
            from apps.soil.models import SoilTest
            kpi['total_soil'] = SoilTest.objects.count()
        except Exception:
            kpi['total_soil'] = 0

        try:
            from apps.crops.models import Crop as CropModel
            kpi['total_crops'] = CropModel.objects.count()
        except Exception:
            kpi['total_crops'] = 0

        try:
            from apps.trials.models import Trial
            kpi['total_trials'] = Trial.objects.count()
        except Exception:
            kpi['total_trials'] = 0

        try:
            from apps.pinn_engine.models import PINNModel
            kpi['total_models'] = PINNModel.objects.count()
        except Exception:
            kpi['total_models'] = 0

        try:
            from apps.advisories.models import AdvisoryDelivery as AD
            kpi['total_deliveries'] = AD.objects.count()
        except Exception:
            kpi['total_deliveries'] = 0

        # ---- Lists for the tables ----
        recent_logins = LoginAudit.objects.select_related('user')[:12]
        integrations_status = IntegrationConfig.objects.all()
        role_breakdown = list(
            User.objects.values('role').annotate(n=Count('id')).order_by('-n')
        )
        all_users = User.objects.order_by('-date_joined')[:50]
        all_farmers = FarmerModel.objects.select_related('county', 'user').order_by('-created_at')[:50]
        all_counties = CountyModel.objects.all()
        pending_advisories = Advisory.objects.filter(
            status=Advisory.Status.DRAFT,
        ).select_related('farmer', 'farm', 'crop')[:25]

        # ---- Phase 2: farms, trials, all advisories ----
        try:
            from apps.farmers.models import Farm as FarmModel2
            all_farms = FarmModel2.objects.select_related('farmer', 'county').order_by('-created_at')[:50]
        except Exception:
            all_farms = []

        try:
            from apps.trials.models import Trial as TrialModel
            all_trials = TrialModel.objects.select_related('site', 'crop', 'county').order_by('-created_at')[:50]
        except Exception:
            all_trials = []

        all_advisories = Advisory.objects.select_related(
            'farmer', 'farm', 'crop',
        ).order_by('-created_at')[:50]

        # ---- Phase 3: PINN models, weather, soil, crops, integrations ----
        try:
            from apps.pinn_engine.models import PINNModel as PINNModel2
            all_pinn_models = PINNModel2.objects.order_by('-updated_at')[:50]
        except Exception:
            all_pinn_models = []

        try:
            from apps.climate.models import WeatherRecord as WeatherRecord2, WeatherStation
            all_weather = WeatherRecord2.objects.select_related('station').order_by('-date')[:50]
            all_weather_stations = WeatherStation.objects.filter(is_active=True)
        except Exception:
            all_weather = []
            all_weather_stations = []

        try:
            from apps.soil.models import SoilTest as SoilTest2
            all_soil_tests = SoilTest2.objects.select_related('farm').order_by('-sampled_on')[:50]
        except Exception:
            all_soil_tests = []

        try:
            from apps.crops.models import Crop as CropModel2, CropCategory
            all_crops = CropModel2.objects.select_related('category').order_by('name')[:100]
            all_crop_categories = CropCategory.objects.all()
        except Exception:
            all_crops = []
            all_crop_categories = []

        try:
            from apps.integrations.models import IntegrationConfig as IntConfig2
            all_integrations = IntConfig2.objects.all()
        except Exception:
            all_integrations = []

    return render(request, template, {
        'stats': stats,
        'recent': recent,
        'can_generate': user.is_kalro_staff or user.is_researcher,
        'can_approve': user.is_kalro_staff,
        'kpi': kpi,
        'recent_logins': recent_logins,
        'integrations_status': integrations_status,
        'role_breakdown': role_breakdown,
        'all_users': all_users,
        'all_farmers': all_farmers,
        'all_counties': all_counties,
        'pending_advisories': pending_advisories,
        'all_farms': all_farms,
        'all_trials': all_trials,
        'all_advisories': all_advisories,
        'all_pinn_models': all_pinn_models,
        'all_weather': all_weather,
        'all_weather_stations': all_weather_stations,
        'all_soil_tests': all_soil_tests,
        'all_crops': all_crops,
        'all_crop_categories': all_crop_categories,
        'all_integrations': all_integrations,
    })


# ==================================================================
# SCOPING HELPER
# ==================================================================
def _scope_advisories_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(farm__county__name__iexact=user.county)
    if user.is_farmer:
        return qs.filter(farmer__user=user)
    return qs.none()


# ==================================================================
# ADVISORY CRUD
# ==================================================================
class AdvisoryListView(KALROStaffRequired, ListView):
    model = Advisory
    template_name = 'advisories/advisory_list.html'
    context_object_name = 'advisories'
    paginate_by = 40
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Advisory.objects.select_related('farmer', 'farm', 'crop', 'created_by')
        qs = _scope_advisories_for(self.request.user, qs)

        q = self.request.GET.get('q')
        kind = self.request.GET.get('kind')
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
        if kind:
            qs = qs.filter(kind=kind)
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kinds'] = Advisory.Kind.choices
        ctx['statuses'] = Advisory.Status.choices
        ctx['priorities'] = Advisory.Priority.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('q', 'kind', 'status', 'priority')}
        ctx['can_generate'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        ctx['can_approve'] = self.request.user.is_kalro_staff
        return ctx


class AdvisoryDetailView(KALROStaffRequired, DetailView):
    model = Advisory
    template_name = 'advisories/advisory_detail.html'
    context_object_name = 'advisory'

    def get_queryset(self):
        qs = Advisory.objects.select_related(
            'farmer', 'farm', 'crop', 'growth_stage', 'inference_run',
            'created_by', 'approved_by',
        )
        return _scope_advisories_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['deliveries'] = self.object.deliveries.all()[:20]
        ctx['feedback'] = self.object.feedback.select_related('reported_by')[:10]
        ctx['feedback_form'] = AdvisoryFeedbackForm(initial={'advisory': self.object})
        ctx['can_approve'] = self.request.user.is_kalro_staff
        return ctx


class AdvisoryCreateView(KALROStaffRequired, CreateView):
    model = Advisory
    form_class = AdvisoryForm
    template_name = 'advisories/advisory_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Advisory created.")
        return super().form_valid(form)


class AdvisoryUpdateView(KALROStaffRequired, UpdateView):
    model = Advisory
    form_class = AdvisoryForm
    template_name = 'advisories/advisory_form.html'

    def get_queryset(self):
        qs = Advisory.objects.all()
        return _scope_advisories_for(self.request.user, qs)

    def form_valid(self, form):
        messages.success(self.request, "Advisory updated.")
        return super().form_valid(form)


# ==================================================================
# EXPLANATION
# ==================================================================
class AdvisoryExplanationView(KALROStaffRequired, DetailView):
    model = Advisory
    template_name = 'advisories/advisory_explanation.html'
    context_object_name = 'advisory'

    def get_queryset(self):
        qs = Advisory.objects.select_related('inference_run')
        return _scope_advisories_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['factors'] = self.object.explanation_factors or []
        ctx['residuals'] = self.object.physics_residuals or {}
        ctx['inference'] = self.object.inference_run
        return ctx


# ==================================================================
# DELIVERY LOG
# ==================================================================
class AdvisoryDeliveryLogView(KALROStaffRequired, ListView):
    model = AdvisoryDelivery
    template_name = 'advisories/advisory_delivery_log.html'
    context_object_name = 'deliveries'
    paginate_by = 60
    ordering = ['-queued_at']

    def get_queryset(self):
        qs = AdvisoryDelivery.objects.select_related('advisory')

        user = self.request.user
        if user.is_field_agent and user.county:
            qs = qs.filter(advisory__farm__county__name__iexact=user.county)
        elif user.is_farmer:
            qs = qs.filter(advisory__farmer__user=user)

        channel = self.request.GET.get('channel')
        status = self.request.GET.get('status')
        advisory_id = self.request.GET.get('advisory')
        if channel:
            qs = qs.filter(channel=channel)
        if status:
            qs = qs.filter(status=status)
        if advisory_id:
            qs = qs.filter(advisory_id=advisory_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['channels'] = AdvisoryDelivery.Channel.choices
        ctx['statuses'] = AdvisoryDelivery.Status.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('channel', 'status', 'advisory')}
        return ctx


# ==================================================================
# GENERATE (single)
# ==================================================================
@researcher_required
def generate_advisory_view(request):
    if request.method == 'POST':
        form = AdvisoryGenerateForm(request.POST)
        if form.is_valid():
            farm = form.cleaned_data['farm']
            crop = form.cleaned_data['crop']
            kind = form.cleaned_data['kind']
            priority = form.cleaned_data['priority']
            notes = form.cleaned_data.get('notes', '')

            advisory = Advisory.objects.create(
                farmer=farm.farmer,
                farm=farm,
                crop=crop,
                kind=kind,
                priority=priority,
                status=Advisory.Status.DRAFT,
                source=Advisory.Source.PINN,
                title=f"Advisory for {farm.name} — {crop.name}",
                body=notes or "Pending PINN generation…",
                created_by=request.user,
            )
            try:
                from apps.integrations.tasks import generate_advisory
                generate_advisory.delay(advisory.pk)
                messages.info(request, f"Advisory #{advisory.pk} queued for generation.")
            except Exception as e:
                messages.warning(
                    request,
                    f"Advisory created as draft, but background task not available: {e}",
                )
            return redirect('advisories:advisory_detail', pk=advisory.pk)
    else:
        form = AdvisoryGenerateForm()

    return render(request, 'advisories/advisory_generate.html', {'form': form})


# ==================================================================
# BULK GENERATE
# ==================================================================
@kalro_admin_required
def bulk_generate_advisories_view(request):
    if request.method == 'POST':
        form = AdvisoryBulkGenerateForm(request.POST)
        if form.is_valid():
            county = form.cleaned_data['county']
            crop = form.cleaned_data['crop']
            kind = form.cleaned_data['kind']
            priority = form.cleaned_data['priority']
            max_farms = form.cleaned_data['max_farms']

            farms = Farm.objects.select_related('farmer').filter(
                county=county, farmer__is_active=True,
            )[:max_farms]

            created = 0
            for farm in farms:
                Advisory.objects.create(
                    farmer=farm.farmer,
                    farm=farm,
                    crop=crop,
                    kind=kind,
                    priority=priority,
                    status=Advisory.Status.DRAFT,
                    source=Advisory.Source.PINN,
                    title=f"Advisory for {farm.name} — {crop.name}",
                    body="Pending PINN bulk generation…",
                    created_by=request.user,
                )
                created += 1

            try:
                from apps.integrations.tasks import bulk_generate_advisories
                bulk_generate_advisories.delay(county.pk, crop.pk, kind)
            except Exception as e:
                messages.warning(request, f"Queued {created} drafts, but task not available: {e}")

            messages.success(request, f"{created} draft advisories created for {county}.")
            return redirect('advisories:advisory_list')
    else:
        form = AdvisoryBulkGenerateForm()

    return render(request, 'advisories/advisory_bulk_generate.html', {'form': form})


# ==================================================================
# FEEDBACK
# ==================================================================
class AdvisoryFeedbackListView(KALROStaffRequired, ListView):
    model = AdvisoryFeedback
    template_name = 'advisories/advisory_feedback_list.html'
    context_object_name = 'feedback_list'
    paginate_by = 40
    ordering = ['-reported_at']

    def get_queryset(self):
        qs = AdvisoryFeedback.objects.select_related('advisory', 'reported_by')

        user = self.request.user
        if user.is_field_agent and user.county:
            qs = qs.filter(advisory__farm__county__name__iexact=user.county)
        elif user.is_farmer:
            qs = qs.filter(advisory__farmer__user=user)

        rating = self.request.GET.get('rating')
        outcome = self.request.GET.get('outcome')
        if rating:
            qs = qs.filter(rating=rating)
        if outcome:
            qs = qs.filter(outcome=outcome)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ratings'] = AdvisoryFeedback.Rating.choices
        ctx['outcomes'] = AdvisoryFeedback.Outcome.choices
        ctx['aggregate'] = AdvisoryFeedback.objects.aggregate(
            avg_rating=Avg('rating'),
        )
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('rating', 'outcome')}
        return ctx


@login_required
def submit_feedback_view(request, advisory_pk):
    advisory = get_object_or_404(Advisory, pk=advisory_pk)
    if request.method == 'POST':
        form = AdvisoryFeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.advisory = advisory
            fb.reported_by = request.user
            fb.save()
            messages.success(request, "Feedback recorded.")
    return redirect('advisories:advisory_detail', pk=advisory.pk)


# ==================================================================
# APPROVE / DISPATCH — public detail-page variants
# ==================================================================
@kalro_admin_required
def approve_advisory_view(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    advisory.status = Advisory.Status.APPROVED
    advisory.approved_by = request.user
    advisory.approved_at = timezone.now()
    advisory.save()
    messages.success(request, "Advisory approved.")
    return redirect('advisories:advisory_detail', pk=pk)


@kalro_admin_required
def dispatch_advisory_view(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    if advisory.status != Advisory.Status.APPROVED:
        messages.error(request, "Only approved advisories can be dispatched.")
        return redirect('advisories:advisory_detail', pk=pk)

    try:
        from apps.integrations.tasks import dispatch_advisory
        dispatch_advisory.delay(advisory.pk)
        messages.info(request, "Advisory queued for dispatch.")
    except Exception as e:
        messages.warning(request, f"Dispatch task not available: {e}")
    return redirect('advisories:advisory_detail', pk=pk)


# ==================================================================
# ADMIN DASHBOARD — USERS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_user_create(request):
    from apps.accounts.forms import UserRegisterForm
    form = UserRegisterForm(request.POST)
    if form.is_valid():
        user = form.save(commit=False)
        user.is_verified = True
        user.save()
        messages.success(request, f"User {user.username} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_user_update(request, pk):
    from apps.accounts.models import User
    from apps.accounts.forms import UserAdminUpdateForm
    user = get_object_or_404(User, pk=pk)
    form = UserAdminUpdateForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        messages.success(request, f"User {user.username} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_user_delete(request, pk):
    from apps.accounts.models import User
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('advisories:advisory_dashboard')
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, "You cannot delete a superuser.")
        return redirect('advisories:advisory_dashboard')
    username = user.username
    user.delete()
    messages.success(request, f"User {username} deleted.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_user_verify(request, pk):
    from apps.accounts.models import User
    user = get_object_or_404(User, pk=pk)
    user.is_verified = True
    user.save(update_fields=['is_verified'])
    messages.success(request, f"{user.username} verified.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_user_unverify(request, pk):
    from apps.accounts.models import User
    user = get_object_or_404(User, pk=pk)
    user.is_verified = False
    user.save(update_fields=['is_verified'])
    messages.warning(request, f"{user.username} unverified.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — FARMERS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_farmer_create(request):
    from apps.farmers.forms import FarmerForm
    form = FarmerForm(request.POST)
    if form.is_valid():
        farmer = form.save(commit=False)
        farmer.registered_by = request.user
        farmer.registration_source = 'ADMIN_DASHBOARD'
        farmer.save()
        messages.success(request, f"Farmer {farmer.full_name} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_farmer_update(request, pk):
    from apps.farmers.models import Farmer
    from apps.farmers.forms import FarmerForm
    farmer = get_object_or_404(Farmer, pk=pk)
    form = FarmerForm(request.POST, instance=farmer)
    if form.is_valid():
        form.save()
        messages.success(request, f"Farmer {farmer.full_name} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_farmer_delete(request, pk):
    from apps.farmers.models import Farmer
    farmer = get_object_or_404(Farmer, pk=pk)
    name = farmer.full_name
    farmer.delete()
    messages.success(request, f"Farmer {name} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — FARMS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_farm_create(request):
    from apps.farmers.models import Farm as FarmM
    from apps.farmers.forms import FarmForm
    form = FarmForm(request.POST)
    if form.is_valid():
        farm = form.save()
        messages.success(request, f"Farm {farm.name} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_farm_update(request, pk):
    from apps.farmers.models import Farm as FarmM
    from apps.farmers.forms import FarmForm
    farm = get_object_or_404(FarmM, pk=pk)
    form = FarmForm(request.POST, instance=farm)
    if form.is_valid():
        form.save()
        messages.success(request, f"Farm {farm.name} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_farm_delete(request, pk):
    from apps.farmers.models import Farm as FarmM
    farm = get_object_or_404(FarmM, pk=pk)
    name = farm.name
    farm.delete()
    messages.success(request, f"Farm {name} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — ADVISORIES CRUD (create, update, approve, dispatch, delete)
# ==================================================================
@kalro_admin_required
@require_POST
def admin_advisory_create(request):
    form = AdvisoryForm(request.POST)
    if form.is_valid():
        adv = form.save(commit=False)
        adv.created_by = request.user
        adv.source = Advisory.Source.MANUAL
        adv.save()
        messages.success(request, f"Advisory #{adv.pk} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_advisory_update(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    form = AdvisoryForm(request.POST, instance=advisory)
    if form.is_valid():
        form.save()
        messages.success(request, f"Advisory #{advisory.pk} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_advisory_approve(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    advisory.status = Advisory.Status.APPROVED
    advisory.approved_by = request.user
    advisory.approved_at = timezone.now()
    advisory.save()
    messages.success(request, f"Advisory #{advisory.pk} approved.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_advisory_dispatch(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    if advisory.status != Advisory.Status.APPROVED:
        messages.error(request, "Only approved advisories can be dispatched.")
        return redirect('advisories:advisory_dashboard')
    try:
        from apps.integrations.tasks import dispatch_advisory
        dispatch_advisory.delay(advisory.pk)
        messages.info(request, f"Advisory #{advisory.pk} queued for dispatch.")
    except Exception as e:
        messages.warning(request, f"Dispatch task not available: {e}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_advisory_delete(request, pk):
    advisory = get_object_or_404(Advisory, pk=pk)
    adv_id = advisory.pk
    advisory.delete()
    messages.success(request, f"Advisory #{adv_id} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — TRIALS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_trial_create(request):
    from apps.trials.forms import TrialForm
    form = TrialForm(request.POST)
    if form.is_valid():
        trial = form.save(commit=False)
        if not trial.lead_researcher:
            trial.lead_researcher = request.user
        trial.save()
        messages.success(request, f"Trial {trial.code} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_trial_update(request, pk):
    from apps.trials.models import Trial
    from apps.trials.forms import TrialForm
    trial = get_object_or_404(Trial, pk=pk)
    form = TrialForm(request.POST, instance=trial)
    if form.is_valid():
        form.save()
        messages.success(request, f"Trial {trial.code} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_trial_delete(request, pk):
    from apps.trials.models import Trial
    trial = get_object_or_404(Trial, pk=pk)
    code = trial.code
    trial.delete()
    messages.success(request, f"Trial {code} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — PINN MODELS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_pinn_create(request):
    from apps.pinn_engine.forms import PINNModelForm
    form = PINNModelForm(request.POST)
    if form.is_valid():
        model = form.save(commit=False)
        model.created_by = request.user
        model.save()
        form.save_m2m()
        messages.success(request, f"PINN model {model.name} created.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_pinn_update(request, pk):
    from apps.pinn_engine.models import PINNModel
    from apps.pinn_engine.forms import PINNModelForm
    model = get_object_or_404(PINNModel, pk=pk)
    form = PINNModelForm(request.POST, instance=model)
    if form.is_valid():
        form.save()
        messages.success(request, f"PINN model {model.name} updated.")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f"{field}: {err}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_pinn_delete(request, pk):
    from apps.pinn_engine.models import PINNModel
    model = get_object_or_404(PINNModel, pk=pk)
    name = model.name
    model.delete()
    messages.success(request, f"PINN model {name} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — WEATHER RECORDS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_weather_create(request):
    from apps.climate.models import WeatherRecord
    data = {
        'station_id': request.POST.get('station') or None,
        'date': request.POST.get('date') or None,
        'rainfall_mm': request.POST.get('rainfall_mm') or None,
        'temp_min_c': request.POST.get('temp_min_c') or None,
        'temp_max_c': request.POST.get('temp_max_c') or None,
        'humidity_pct': request.POST.get('humidity_pct') or None,
    }
    try:
        rec = WeatherRecord.objects.create(
            station_id=data['station_id'],
            date=data['date'],
            rainfall_mm=data['rainfall_mm'],
            temp_min_c=data['temp_min_c'],
            temp_max_c=data['temp_max_c'],
            humidity_pct=data['humidity_pct'],
        )
        messages.success(request, f"Weather record for {rec.date} created.")
    except Exception as e:
        messages.error(request, f"Could not create record: {e}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_weather_update(request, pk):
    from apps.climate.models import WeatherRecord
    rec = get_object_or_404(WeatherRecord, pk=pk)
    for field in ('rainfall_mm', 'temp_min_c', 'temp_max_c', 'humidity_pct'):
        val = request.POST.get(field)
        setattr(rec, field, val if val else None)
    rec.save()
    messages.success(request, f"Weather record {rec.date} updated.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_weather_delete(request, pk):
    from apps.climate.models import WeatherRecord
    rec = get_object_or_404(WeatherRecord, pk=pk)
    d = rec.date
    rec.delete()
    messages.success(request, f"Weather record {d} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — SOIL TESTS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_soil_create(request):
    from apps.soil.models import SoilTest
    try:
        s = SoilTest.objects.create(
            farm_id=request.POST.get('farm') or None,
            sample_id=request.POST.get('sample_id'),
            sampled_on=request.POST.get('sampled_on'),
            lab=request.POST.get('lab') or 'KALRO',
            ph=request.POST.get('ph') or None,
            organic_carbon_pct=request.POST.get('organic_carbon_pct') or None,
            nitrogen_pct=request.POST.get('nitrogen_pct') or None,
            phosphorus_ppm=request.POST.get('phosphorus_ppm') or None,
            potassium_ppm=request.POST.get('potassium_ppm') or None,
            texture=request.POST.get('texture') or '',
        )
        messages.success(request, f"Soil test {s.sample_id} created.")
    except Exception as e:
        messages.error(request, f"Could not create soil test: {e}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_soil_update(request, pk):
    from apps.soil.models import SoilTest
    s = get_object_or_404(SoilTest, pk=pk)
    for field in ('ph', 'nitrogen_pct', 'phosphorus_ppm', 'potassium_ppm'):
        val = request.POST.get(field)
        setattr(s, field, val if val else None)
    s.save()
    messages.success(request, f"Soil test {s.sample_id} updated.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_soil_delete(request, pk):
    from apps.soil.models import SoilTest
    s = get_object_or_404(SoilTest, pk=pk)
    sid = s.sample_id
    s.delete()
    messages.success(request, f"Soil test {sid} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — CROPS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_crop_create(request):
    from apps.crops.models import Crop
    try:
        c = Crop.objects.create(
            name=request.POST.get('name'),
            scientific_name=request.POST.get('scientific_name') or '',
            category_id=request.POST.get('category') or None,
            season=request.POST.get('season') or 'BOTH',
            water_requirement_mm=request.POST.get('water_requirement_mm') or None,
            days_to_maturity=request.POST.get('days_to_maturity') or None,
            is_active=bool(request.POST.get('is_active')),
        )
        messages.success(request, f"Crop {c.name} created.")
    except Exception as e:
        messages.error(request, f"Could not create crop: {e}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_crop_update(request, pk):
    from apps.crops.models import Crop
    c = get_object_or_404(Crop, pk=pk)
    c.name = request.POST.get('name') or c.name
    c.scientific_name = request.POST.get('scientific_name') or c.scientific_name
    c.water_requirement_mm = request.POST.get('water_requirement_mm') or c.water_requirement_mm
    c.days_to_maturity = request.POST.get('days_to_maturity') or c.days_to_maturity
    c.is_active = bool(request.POST.get('is_active'))
    c.save()
    messages.success(request, f"Crop {c.name} updated.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_crop_delete(request, pk):
    from apps.crops.models import Crop
    c = get_object_or_404(Crop, pk=pk)
    name = c.name
    c.delete()
    messages.success(request, f"Crop {name} deleted.")
    return redirect('advisories:advisory_dashboard')


# ==================================================================
# ADMIN DASHBOARD — INTEGRATION CONFIGS CRUD
# ==================================================================
@kalro_admin_required
@require_POST
def admin_integration_create(request):
    from apps.integrations.models import IntegrationConfig
    try:
        i = IntegrationConfig.objects.create(
            provider=request.POST.get('provider'),
            display_name=request.POST.get('display_name') or '',
            base_url=request.POST.get('base_url') or '',
            auth_type=request.POST.get('auth_type') or 'APIKEY',
            api_key=request.POST.get('api_key') or '',
            api_secret=request.POST.get('api_secret') or '',
            is_active=bool(request.POST.get('is_active')),
            is_sandbox=bool(request.POST.get('is_sandbox')),
        )
        messages.success(request, f"{i.get_provider_display()} config created.")
    except Exception as e:
        messages.error(request, f"Could not create integration: {e}")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_integration_update(request, pk):
    from apps.integrations.models import IntegrationConfig
    i = get_object_or_404(IntegrationConfig, pk=pk)
    i.display_name = request.POST.get('display_name') or i.display_name
    i.base_url = request.POST.get('base_url') or i.base_url
    i.api_key = request.POST.get('api_key') or i.api_key
    i.api_secret = request.POST.get('api_secret') or i.api_secret
    i.is_active = bool(request.POST.get('is_active'))
    i.is_sandbox = bool(request.POST.get('is_sandbox'))
    i.save()
    messages.success(request, f"{i.get_provider_display()} updated.")
    return redirect('advisories:advisory_dashboard')


@kalro_admin_required
@require_POST
def admin_integration_delete(request, pk):
    from apps.integrations.models import IntegrationConfig
    i = get_object_or_404(IntegrationConfig, pk=pk)
    label = i.get_provider_display()
    i.delete()
    messages.success(request, f"{label} config deleted.")
    return redirect('advisories:advisory_dashboard')