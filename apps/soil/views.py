from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    KALROStaffRequired, KALROAdminRequired, kalro_admin_required,
)
from apps.farmers.models import County, Farm
from .forms import SoilTestForm, NutrientProfileForm, MarketPriceForm
from .models import SoilTest, NutrientProfile, MarketPrice, AgDataSyncLog


# ==================================================================
# SCOPING HELPERS
# ==================================================================
def _scope_soil_tests_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(farm__county__name__iexact=user.county)
    if user.is_farmer:
        return qs.filter(farm__farmer__user=user)
    return qs.none()


def _scope_prices_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(county__name__iexact=user.county)
    return qs


def _counties_for(user):
    if user.is_field_agent and user.county:
        return County.objects.filter(name__iexact=user.county)
    return County.objects.all()


# ==================================================================
# SOIL TESTS
# ==================================================================
class SoilTestListView(KALROStaffRequired, ListView):
    model = SoilTest
    template_name = 'soil/soiltest_list.html'
    context_object_name = 'tests'
    paginate_by = 40
    ordering = ['-sampled_on']

    def get_queryset(self):
        qs = SoilTest.objects.select_related('farm', 'farm__farmer', 'farm__county')
        qs = _scope_soil_tests_for(self.request.user, qs)

        q = self.request.GET.get('q')
        county = self.request.GET.get('county')
        lab = self.request.GET.get('lab')
        if q:
            qs = qs.filter(
                Q(sample_id__icontains=q) |
                Q(farm__name__icontains=q) |
                Q(farm__farmer__full_name__icontains=q)
            )
        if county:
            qs = qs.filter(farm__county_id=county)
        if lab:
            qs = qs.filter(lab=lab)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['counties'] = _counties_for(self.request.user)
        ctx['labs'] = SoilTest.Lab.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('q', 'county', 'lab')}
        return ctx


class SoilTestDetailView(KALROStaffRequired, DetailView):
    model = SoilTest
    template_name = 'soil/soiltest_detail.html'
    context_object_name = 'test'

    def get_queryset(self):
        qs = SoilTest.objects.select_related('farm', 'farm__farmer', 'farm__county')
        return _scope_soil_tests_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profiles = NutrientProfile.objects.all()
        if self.object.texture:
            profiles = profiles.filter(
                Q(soil_texture__iexact=self.object.texture) | Q(soil_texture='')
            )
        ctx['profiles'] = profiles[:5]
        ctx['history'] = (
            SoilTest.objects
            .filter(farm=self.object.farm)
            .exclude(pk=self.object.pk)
            .order_by('-sampled_on')[:10]
        )
        return ctx


class SoilTestCreateView(KALROStaffRequired, CreateView):
    model = SoilTest
    form_class = SoilTestForm
    template_name = 'soil/soiltest_form.html'

    def get_initial(self):
        initial = super().get_initial()
        farm_id = self.request.GET.get('farm')
        if farm_id:
            initial['farm'] = farm_id
        initial['sampled_by'] = self.request.user
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Soil test saved.")
        return super().form_valid(form)


class SoilTestUpdateView(KALROStaffRequired, UpdateView):
    model = SoilTest
    form_class = SoilTestForm
    template_name = 'soil/soiltest_form.html'

    def get_queryset(self):
        qs = SoilTest.objects.all()
        return _scope_soil_tests_for(self.request.user, qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Soil test updated.")
        return super().form_valid(form)


# ==================================================================
# NUTRIENT PROFILES
# ==================================================================
class NutrientProfileListView(KALROStaffRequired, ListView):
    model = NutrientProfile
    template_name = 'soil/nutrient_profile.html'
    context_object_name = 'profiles'
    paginate_by = 40

    def get_queryset(self):
        qs = NutrientProfile.objects.select_related('crop')
        crop = self.request.GET.get('crop')
        if crop:
            qs = qs.filter(crop_id=crop)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.crops.models import Crop
        ctx['crops'] = Crop.objects.all()
        ctx['current_crop'] = self.request.GET.get('crop', '')
        return ctx


class NutrientProfileCreateView(KALROAdminRequired, CreateView):
    model = NutrientProfile
    form_class = NutrientProfileForm
    template_name = 'soil/nutrient_profile_form.html'
    success_url = reverse_lazy('soil:nutrient_profile')

    def form_valid(self, form):
        messages.success(self.request, "Nutrient profile created.")
        return super().form_valid(form)


class NutrientProfileUpdateView(KALROAdminRequired, UpdateView):
    model = NutrientProfile
    form_class = NutrientProfileForm
    template_name = 'soil/nutrient_profile_form.html'
    success_url = reverse_lazy('soil:nutrient_profile')

    def form_valid(self, form):
        messages.success(self.request, "Nutrient profile updated.")
        return super().form_valid(form)


# ==================================================================
# MARKET PRICES
# ==================================================================
class MarketPriceListView(KALROStaffRequired, ListView):
    model = MarketPrice
    template_name = 'soil/marketprice_list.html'
    context_object_name = 'prices'
    paginate_by = 50
    ordering = ['-observed_on']

    def get_queryset(self):
        qs = MarketPrice.objects.select_related('county')
        qs = _scope_prices_for(self.request.user, qs)

        commodity = self.request.GET.get('commodity')
        county = self.request.GET.get('county')
        if commodity:
            qs = qs.filter(commodity=commodity)
        if county:
            qs = qs.filter(county_id=county)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['commodities'] = MarketPrice.Commodity.choices
        ctx['counties'] = _counties_for(self.request.user)
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('commodity', 'county')}
        return ctx


class MarketPriceCreateView(KALROStaffRequired, CreateView):
    model = MarketPrice
    form_class = MarketPriceForm
    template_name = 'soil/marketprice_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Market price recorded.")
        return super().form_valid(form)


class MarketPriceUpdateView(KALROStaffRequired, UpdateView):
    model = MarketPrice
    form_class = MarketPriceForm
    template_name = 'soil/marketprice_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Market price updated.")
        return super().form_valid(form)


# ==================================================================
# AGDATA SYNC
# ==================================================================
@kalro_admin_required
def sync_agdata_view(request):
    if request.method == 'POST':
        log = AgDataSyncLog.objects.create(
            triggered_by=request.user,
            status=AgDataSyncLog.Status.RUNNING,
        )
        try:
            from apps.integrations.tasks import sync_agdata
            sync_agdata.delay(log.pk)
            messages.info(request, f"AgData sync #{log.pk} queued.")
        except Exception as e:
            log.status = AgDataSyncLog.Status.FAILED
            log.error_log = str(e)
            log.finished_at = timezone.now()
            log.save()
            messages.error(request, f"Could not queue sync: {e}")
        return redirect('soil:sync_agdata')

    recent = AgDataSyncLog.objects.all()[:20]
    return render(request, 'soil/sync_agdata.html', {'recent': recent})