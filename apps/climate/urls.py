from django.urls import path

from . import views

app_name = 'climate'

urlpatterns = [
    # Weather records
    path('', views.WeatherRecordListView.as_view(), name='weatherrecord_list'),
    path('records/create/', views.WeatherRecordCreateView.as_view(), name='weatherrecord_create'),
    path('records/<int:pk>/', views.WeatherRecordDetailView.as_view(), name='weatherrecord_detail'),
    path('records/<int:pk>/edit/', views.WeatherRecordUpdateView.as_view(), name='weatherrecord_update'),

    # Forecasts
    path('forecasts/', views.ForecastListView.as_view(), name='forecast_list'),

    # Alerts
    path('alerts/drought/', views.DroughtAlertListView.as_view(), name='drought_alert_list'),
    path('alerts/flood/', views.FloodAlertListView.as_view(), name='flood_alert_list'),
    path('alerts/create/', views.climate_alert_create, name='climate_alert_create'),

    # Charts & sync
    path('rainfall-chart/', views.rainfall_chart_view, name='rainfall_chart'),
    path('sync/kaop/', views.sync_kaop_view, name='sync_kaop'),
]