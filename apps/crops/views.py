from django.contrib import messages
from django.db.models import Q, Prefetch
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    KALROStaffRequired, KALROAdminRequired, AnyAuthenticated,
)
from apps.farmers.models import County
from .forms import CropForm, GrowthStageForm, CropCalendarForm
from .models import Crop, CropCategory, GrowthStage, CropCalendar


# ==================================================================
# SCOPING HELPERS
# ==================================================================
def _counties_for(user):
    if user.is_field_agent and user.county:
        return County.objects.filter(name__iexact=user.county)
    return County.objects.all()


# ==================================================================
# CROPS
# ==================================================================
class CropListView(AnyAuthenticated, ListView):
    """Anyone logged in can browse crops; edit is restricted below."""
    model = Crop
    template_name = 'crops/crop_list.html'
    context_object_name = 'crops'
    paginate_by = 40
    ordering = ['name']

    def get_queryset(self):
        qs = Crop.objects.select_related('category')
        q = self.request.GET.get('q')
        category = self.request.GET.get('category')
        season = self.request.GET.get('season')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(scientific_name__icontains=q))
        if category:
            qs = qs.filter(category_id=category)
        if season:
            qs = qs.filter(season=season)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = CropCategory.objects.all()
        ctx['seasons'] = Crop.Season.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('q', 'category', 'season')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class CropDetailView(AnyAuthenticated, DetailView):
    model = Crop
    template_name = 'crops/crop_detail.html'
    context_object_name = 'crop'

    def get_queryset(self):
        return Crop.objects.select_related('category').prefetch_related(
            Prefetch('growth_stages', queryset=GrowthStage.objects.order_by('order')),
            Prefetch('calendars', queryset=CropCalendar.objects.select_related('county')),
            'nutrient_profiles',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class CropCreateView(KALROAdminRequired, CreateView):
    model = Crop
    form_class = CropForm
    template_name = 'crops/crop_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Crop created.")
        return super().form_valid(form)


class CropUpdateView(KALROAdminRequired, UpdateView):
    model = Crop
    form_class = CropForm
    template_name = 'crops/crop_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Crop updated.")
        return super().form_valid(form)


# ==================================================================
# GROWTH STAGES
# ==================================================================
class GrowthStageListView(AnyAuthenticated, ListView):
    model = GrowthStage
    template_name = 'crops/growthstage_list.html'
    context_object_name = 'stages'
    paginate_by = 60
    ordering = ['crop', 'order']

    def get_queryset(self):
        qs = GrowthStage.objects.select_related('crop')
        crop = self.request.GET.get('crop')
        if crop:
            qs = qs.filter(crop_id=crop)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['crops'] = Crop.objects.all()
        ctx['current_crop'] = self.request.GET.get('crop', '')
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class GrowthStageCreateView(KALROAdminRequired, CreateView):
    model = GrowthStage
    form_class = GrowthStageForm
    template_name = 'crops/growthstage_form.html'
    success_url = reverse_lazy('crops:growthstage_list')

    def get_initial(self):
        initial = super().get_initial()
        crop_id = self.request.GET.get('crop')
        if crop_id:
            initial['crop'] = crop_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Growth stage added.")
        return super().form_valid(form)


class GrowthStageUpdateView(KALROAdminRequired, UpdateView):
    model = GrowthStage
    form_class = GrowthStageForm
    template_name = 'crops/growthstage_form.html'
    success_url = reverse_lazy('crops:growthstage_list')

    def form_valid(self, form):
        messages.success(self.request, "Growth stage updated.")
        return super().form_valid(form)


# ==================================================================
# CROP REQUIREMENTS (PINN view)
# ==================================================================
class CropRequirementsView(AnyAuthenticated, DetailView):
    model = Crop
    template_name = 'crops/crop_requirements.html'
    context_object_name = 'crop'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stages'] = self.object.growth_stages.order_by('order')
        ctx['profiles'] = (
            self.object.nutrient_profiles.all()
            if hasattr(self.object, 'nutrient_profiles') else []
        )
        return ctx


# ==================================================================
# CROP CALENDAR
# ==================================================================
class CropCalendarView(AnyAuthenticated, ListView):
    model = CropCalendar
    template_name = 'crops/crop_calendar.html'
    context_object_name = 'calendars'
    paginate_by = 40

    def get_queryset(self):
        qs = CropCalendar.objects.select_related('crop', 'county')
        crop = self.request.GET.get('crop')
        county = self.request.GET.get('county')
        aez = self.request.GET.get('aez')
        if crop:
            qs = qs.filter(crop_id=crop)
        if county:
            qs = qs.filter(county_id=county)
        if aez:
            qs = qs.filter(aez=aez)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['crops'] = Crop.objects.all()
        ctx['counties'] = _counties_for(self.request.user)
        ctx['aez_choices'] = CropCalendar.AEZ.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('crop', 'county', 'aez')}
        ctx['month_range'] = range(1, 13)
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class CropCalendarCreateView(KALROAdminRequired, CreateView):
    model = CropCalendar
    form_class = CropCalendarForm
    template_name = 'crops/crop_calendar_form.html'
    success_url = reverse_lazy('crops:crop_calendar')

    def form_valid(self, form):
        messages.success(self.request, "Calendar entry added.")
        return super().form_valid(form)


class CropCalendarUpdateView(KALROAdminRequired, UpdateView):
    model = CropCalendar
    form_class = CropCalendarForm
    template_name = 'crops/crop_calendar_form.html'
    success_url = reverse_lazy('crops:crop_calendar')

    def form_valid(self, form):
        messages.success(self.request, "Calendar entry updated.")
        return super().form_valid(form)