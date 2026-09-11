from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    KALROAdminRequired, kalro_admin_required,
)
from .forms import IntegrationConfigForm, SyncTriggerForm
from .models import IntegrationConfig, SyncLog, WebhookEvent


# ==================================================================
# INTEGRATION CONFIG
# ==================================================================
class IntegrationConfigListView(KALROAdminRequired, ListView):
    model = IntegrationConfig
    template_name = 'integrations/integrationconfig_list.html'
    context_object_name = 'configs'
    ordering = ['provider']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['providers'] = IntegrationConfig.Provider.choices
        return ctx


class IntegrationConfigCreateView(KALROAdminRequired, CreateView):
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    template_name = 'integrations/integrationconfig_form.html'
    success_url = reverse_lazy('integrations:integrationconfig_list')

    def form_valid(self, form):
        messages.success(self.request, "Integration config created.")
        return super().form_valid(form)


class IntegrationConfigUpdateView(KALROAdminRequired, UpdateView):
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    template_name = 'integrations/integrationconfig_form.html'
    success_url = reverse_lazy('integrations:integrationconfig_list')

    def form_valid(self, form):
        messages.success(self.request, "Integration config updated.")
        return super().form_valid(form)


# ==================================================================
# SYNC LOGS
# ==================================================================
class SyncLogListView(KALROAdminRequired, ListView):
    model = SyncLog
    template_name = 'integrations/synclog_list.html'
    context_object_name = 'logs'
    paginate_by = 60
    ordering = ['-started_at']

    def get_queryset(self):
        qs = SyncLog.objects.select_related('config', 'triggered_by')
        provider = self.request.GET.get('provider')
        operation = self.request.GET.get('operation')
        status = self.request.GET.get('status')
        if provider:
            qs = qs.filter(provider=provider)
        if operation:
            qs = qs.filter(operation=operation)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['providers'] = IntegrationConfig.Provider.choices
        ctx['operations'] = SyncLog.Operation.choices
        ctx['statuses'] = SyncLog.Status.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('provider', 'operation', 'status')}
        return ctx


class SyncLogDetailView(KALROAdminRequired, DetailView):
    model = SyncLog
    template_name = 'integrations/synclog_detail.html'
    context_object_name = 'log'


# ==================================================================
# WEBHOOK EVENTS
# ==================================================================
class WebhookEventListView(KALROAdminRequired, ListView):
    model = WebhookEvent
    template_name = 'integrations/webhookevent_list.html'
    context_object_name = 'events'
    paginate_by = 60
    ordering = ['-received_at']

    def get_queryset(self):
        qs = WebhookEvent.objects.select_related('related_sync_log')
        provider = self.request.GET.get('provider')
        status = self.request.GET.get('status')
        if provider:
            qs = qs.filter(provider=provider)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['providers'] = IntegrationConfig.Provider.choices
        ctx['statuses'] = WebhookEvent.Status.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('provider', 'status')}
        return ctx


class WebhookEventDetailView(KALROAdminRequired, DetailView):
    model = WebhookEvent
    template_name = 'integrations/webhookevent_detail.html'
    context_object_name = 'event'


# ==================================================================
# PER-PROVIDER DASHBOARDS
# ==================================================================
def _provider_dashboard(request, provider: str, template: str, extra_ctx=None):
    config = IntegrationConfig.objects.filter(provider=provider).first()
    logs = SyncLog.objects.filter(provider=provider)[:30]
    stats = SyncLog.objects.filter(provider=provider).aggregate(
        total=Count('id'),
    )
    ctx = {
        'config': config,
        'logs': logs,
        'stats': stats,
        'health_check_form': SyncTriggerForm(initial={
            'provider': provider,
            'operation': SyncLog.Operation.HEALTH_CHECK,
        }),
        'provider': provider,
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template, ctx)


@kalro_admin_required
def kaop_dashboard_view(request):
    from apps.climate.models import WeatherStation, WeatherRecord, KAOPSyncLog
    return _provider_dashboard(
        request,
        IntegrationConfig.Provider.KAOP,
        'integrations/kaop_dashboard.html',
        {
            'station_count': WeatherStation.objects.filter(is_active=True).count(),
            'record_count': WeatherRecord.objects.count(),
            'recent_syncs': KAOPSyncLog.objects.all()[:10],
        },
    )


@kalro_admin_required
def agdata_dashboard_view(request):
    from apps.soil.models import SoilTest, MarketPrice, AgDataSyncLog
    return _provider_dashboard(
        request,
        IntegrationConfig.Provider.AGDATA,
        'integrations/agdata_dashboard.html',
        {
            'soil_test_count': SoilTest.objects.count(),
            'market_price_count': MarketPrice.objects.count(),
            'recent_syncs': AgDataSyncLog.objects.all()[:10],
        },
    )


@kalro_admin_required
def selector_dashboard_view(request):
    from apps.advisories.models import AdvisoryDelivery
    return _provider_dashboard(
        request,
        IntegrationConfig.Provider.SELECTOR,
        'integrations/selector_dashboard.html',
        {
            'delivery_count': AdvisoryDelivery.objects.filter(
                channel=AdvisoryDelivery.Channel.SELECTOR,
            ).count(),
            'recent_deliveries': AdvisoryDelivery.objects.filter(
                channel=AdvisoryDelivery.Channel.SELECTOR,
            )[:20],
        },
    )


@kalro_admin_required
def ishamba_dashboard_view(request):
    from apps.advisories.models import AdvisoryDelivery
    return _provider_dashboard(
        request,
        IntegrationConfig.Provider.ISHAMBA,
        'integrations/ishamba_dashboard.html',
        {
            'sms_count': AdvisoryDelivery.objects.filter(
                channel=AdvisoryDelivery.Channel.SMS,
            ).count(),
            'recent_sms': AdvisoryDelivery.objects.filter(
                channel=AdvisoryDelivery.Channel.SMS,
            )[:20],
        },
    )


# ==================================================================
# MANUAL SYNC TRIGGER
# ==================================================================
@kalro_admin_required
def trigger_sync_view(request):
    if request.method == 'POST':
        form = SyncTriggerForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            operation = form.cleaned_data['operation']
            dry_run = form.cleaned_data['dry_run']

            task_map = {
                SyncLog.Operation.PULL_WEATHER: 'integrations.sync_kaop',
                SyncLog.Operation.PULL_FORECAST: 'integrations.sync_kaop',
                SyncLog.Operation.PULL_SOIL: 'integrations.sync_agdata',
                SyncLog.Operation.PULL_MARKET: 'integrations.sync_agdata',
                SyncLog.Operation.HEALTH_CHECK: 'integrations.health_check',
            }

            task_name = task_map.get(operation)
            if not task_name:
                messages.error(request, f"No task mapped for operation {operation}.")
                return redirect('integrations:integrationconfig_list')

            if dry_run:
                messages.info(request, f"Dry-run: would queue {task_name} for {provider}.")
                return redirect('integrations:integrationconfig_list')

            try:
                from . import tasks
                task_fn = getattr(tasks, task_name.split('.')[-1])
                if operation == SyncLog.Operation.HEALTH_CHECK:
                    task_fn.delay(provider)
                else:
                    task_fn.delay()
                messages.success(request, f"Queued {task_name} for {provider}.")
            except Exception as e:
                messages.error(request, f"Could not queue task: {e}")

            return redirect('integrations:integrationconfig_list')
    else:
        form = SyncTriggerForm()

    return render(request, 'integrations/integrationconfig_form.html', {
        'form': form, 'form_title': 'Trigger Manual Sync',
    })