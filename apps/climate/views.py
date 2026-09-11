from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    KALROStaffRequired, KALROAdminRequired, kalro_admin_required,
)
from apps.farmers.models import County
from .forms import (
    WeatherRecordForm, WeatherStationForm, ClimateAlertForm, ForecastFilterForm,
)
from .models import (
    WeatherStation, WeatherRecord, Forecast, ClimateAlert, KAOPSyncLog,
)


# ==================================================================
# SCOPING HELPERS
# ==================================================================
def _scope_stations_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(county__name__iexact=user.county)
    return qs.none()


def _scope_records_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(station__county__name__iexact=user.county)
    return qs.none()


def _scope_alerts_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(county__name__iexact=user.county)
    return qs.none()


def _counties_for(user):
    if user.is_field_agent and user.county:
        return County.objects.filter(name__iexact=user.county)
    return County.objects.all()


# ==================================================================
# WEATHER RECORDS
# ==================================================================
class WeatherRecordListView(KALROStaffRequired, ListView):
    model = WeatherRecord
    template_name = 'climate/weatherrecord_list.html'
    context_object_name = 'records'
    paginate_by = 60
    ordering = ['-date']

    def get_queryset(self):
        qs = WeatherRecord.objects.select_related('station', 'station__county')
        qs = _scope_records_for(self.request.user, qs)

        station = self.request.GET.get('station')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        county = self.request.GET.get('county')

        if station:
            qs = qs.filter(station_id=station)
        if county:
            qs = qs.filter(station__county_id=county)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stations'] = _scope_stations_for(
            self.request.user, WeatherStation.objects.filter(is_active=True)
        )
        ctx['counties'] = _counties_for(self.request.user)
        ctx['current'] = {k: self.request.GET.get(k, '') for k in
                          ('station', 'county', 'date_from', 'date_to')}
        return ctx


class WeatherRecordDetailView(KALROStaffRequired, DetailView):
    model = WeatherRecord
    template_name = 'climate/weatherrecord_detail.html'
    context_object_name = 'record'

    def get_queryset(self):
        qs = WeatherRecord.objects.select_related('station', 'station__county')
        return _scope_records_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent'] = (
            WeatherRecord.objects
            .filter(station=self.object.station, date__lte=self.object.date)
            .order_by('-date')[:14]
        )
        return ctx


class WeatherRecordCreateView(KALROStaffRequired, CreateView):
    model = WeatherRecord
    form_class = WeatherRecordForm
    template_name = 'climate/weatherrecord_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Weather record saved.")
        return super().form_valid(form)


class WeatherRecordUpdateView(KALROStaffRequired, UpdateView):
    model = WeatherRecord
    form_class = WeatherRecordForm
    template_name = 'climate/weatherrecord_form.html'

    def get_queryset(self):
        qs = WeatherRecord.objects.all()
        return _scope_records_for(self.request.user, qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Weather record updated.")
        return super().form_valid(form)


# ==================================================================
# FORECASTS
# ==================================================================
class ForecastListView(KALROStaffRequired, ListView):
    model = Forecast
    template_name = 'climate/forecast_list.html'
    context_object_name = 'forecasts'
    paginate_by = 50
    ordering = ['-issued_at']

    def get_queryset(self):
        qs = Forecast.objects.select_related('station', 'station__county')
        qs = _scope_records_for(self.request.user, qs)

        station = self.request.GET.get('station')
        horizon = self.request.GET.get('horizon')
        if station:
            qs = qs.filter(station_id=station)
        if horizon:
            qs = qs.filter(horizon=horizon)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = ForecastFilterForm(self.request.GET or None)
        ctx['counties'] = _counties_for(self.request.user)
        return ctx


# ==================================================================
# ALERTS
# ==================================================================
class DroughtAlertListView(KALROStaffRequired, ListView):
    model = ClimateAlert
    template_name = 'climate/drought_alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 40

    def get_queryset(self):
        qs = ClimateAlert.objects.filter(
            kind=ClimateAlert.Kind.DROUGHT,
        ).select_related('county').order_by('-issued_at')
        return _scope_alerts_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kind'] = 'Drought'
        ctx['kind_slug'] = 'drought'
        return ctx


class FloodAlertListView(KALROStaffRequired, ListView):
    model = ClimateAlert
    template_name = 'climate/flood_alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 40

    def get_queryset(self):
        qs = ClimateAlert.objects.filter(
            kind=ClimateAlert.Kind.FLOOD,
        ).select_related('county').order_by('-issued_at')
        return _scope_alerts_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kind'] = 'Flood'
        ctx['kind_slug'] = 'flood'
        return ctx


@kalro_admin_required
def climate_alert_create(request):
    if request.method == 'POST':
        form = ClimateAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.issued_by = request.user
            alert.save()
            form.save_m2m()
            messages.success(request, "Climate alert issued.")
            return redirect('climate:drought_alert_list')
    else:
        form = ClimateAlertForm()
    return render(request, 'climate/weatherrecord_form.html', {
        'form': form, 'form_title': 'Issue Climate Alert',
    })


# ==================================================================
# RAINFALL CHART
# ==================================================================
@login_required
def rainfall_chart_view(request):
    station_id = request.GET.get('station')
    days = int(request.GET.get('days', 30))
    stations = _scope_stations_for(
        request.user, WeatherStation.objects.filter(is_active=True)
    )

    station = None
    labels, rainfall, temp_min, temp_max = [], [], [], []
    if station_id:
        station = get_object_or_404(
            _scope_stations_for(request.user, WeatherStation.objects.all()),
            pk=station_id,
        )
        since = timezone.now().date() - timezone.timedelta(days=days)
        records = (
            WeatherRecord.objects
            .filter(station=station, date__gte=since)
            .order_by('date')
        )
        labels = [r.date.strftime('%Y-%m-%d') for r in records]
        rainfall = [float(r.rainfall_mm or 0) for r in records]
        temp_min = [float(r.temp_min_c or 0) for r in records]
        temp_max = [float(r.temp_max_c or 0) for r in records]

    return render(request, 'climate/rainfall_chart.html', {
        'stations': stations,
        'station': station,
        'labels': labels,
        'rainfall': rainfall,
        'temp_min': temp_min,
        'temp_max': temp_max,
        'days': days,
    })


# ==================================================================
# KAOP SYNC
# ==================================================================
@kalro_admin_required
def sync_kaop_view(request):
    if request.method == 'POST':
        log = KAOPSyncLog.objects.create(
            triggered_by=request.user,
            status=KAOPSyncLog.Status.RUNNING,
        )
        try:
            from apps.integrations.tasks import sync_kaop
            sync_kaop.delay(log.pk)
            messages.info(request, f"KAOP sync #{log.pk} queued.")
        except Exception as e:
            log.status = KAOPSyncLog.Status.FAILED
            log.error_log = str(e)
            log.finished_at = timezone.now()
            log.save()
            messages.error(request, f"Could not queue sync: {e}")
        return redirect('climate:sync_kaop')

    recent = KAOPSyncLog.objects.all()[:20]
    return render(request, 'climate/sync_kaop.html', {'recent': recent})