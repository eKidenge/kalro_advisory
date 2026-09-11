from django.urls import path

from . import views

app_name = 'integrations'

urlpatterns = [
    # Configs
    path('', views.IntegrationConfigListView.as_view(), name='integrationconfig_list'),
    path('create/', views.IntegrationConfigCreateView.as_view(), name='integrationconfig_create'),
    path('<int:pk>/edit/', views.IntegrationConfigUpdateView.as_view(), name='integrationconfig_update'),

    # Sync logs
    path('syncs/', views.SyncLogListView.as_view(), name='synclog_list'),
    path('syncs/<int:pk>/', views.SyncLogDetailView.as_view(), name='synclog_detail'),

    # Webhook events
    path('webhooks/', views.WebhookEventListView.as_view(), name='webhookevent_list'),
    path('webhooks/<int:pk>/', views.WebhookEventDetailView.as_view(), name='webhookevent_detail'),

    # Per-provider dashboards
    path('kaop/', views.kaop_dashboard_view, name='kaop_dashboard'),
    path('agdata/', views.agdata_dashboard_view, name='agdata_dashboard'),
    path('selector/', views.selector_dashboard_view, name='selector_dashboard'),
    path('ishamba/', views.ishamba_dashboard_view, name='ishamba_dashboard'),

    # Trigger
    path('trigger/', views.trigger_sync_view, name='trigger_sync'),
]