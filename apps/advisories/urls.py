from django.urls import path

from . import views

app_name = 'advisories'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='advisory_dashboard'),

    # ----------------------------------------------------------------
    # Admin dashboard — Users CRUD
    # ----------------------------------------------------------------
    path('admin/user/add/',               views.admin_user_create,   name='admin_user_create'),
    path('admin/user/<int:pk>/edit/',     views.admin_user_update,   name='admin_user_update'),
    path('admin/user/<int:pk>/delete/',   views.admin_user_delete,   name='admin_user_delete'),
    path('admin/user/<int:pk>/verify/',   views.admin_user_verify,   name='admin_user_verify'),
    path('admin/user/<int:pk>/unverify/', views.admin_user_unverify, name='admin_user_unverify'),

    # ----------------------------------------------------------------
    # Admin dashboard — Farmers CRUD
    # ----------------------------------------------------------------
    path('admin/farmer/add/',             views.admin_farmer_create, name='admin_farmer_create'),
    path('admin/farmer/<int:pk>/edit/',   views.admin_farmer_update, name='admin_farmer_update'),
    path('admin/farmer/<int:pk>/delete/', views.admin_farmer_delete, name='admin_farmer_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Farms CRUD
    # ----------------------------------------------------------------
    path('admin/farm/add/',             views.admin_farm_create, name='admin_farm_create'),
    path('admin/farm/<int:pk>/edit/',   views.admin_farm_update, name='admin_farm_update'),
    path('admin/farm/<int:pk>/delete/', views.admin_farm_delete, name='admin_farm_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Advisories CRUD + actions
    # ----------------------------------------------------------------
    path('admin/advisory/add/',               views.admin_advisory_create,   name='admin_advisory_create'),
    path('admin/advisory/<int:pk>/edit/',     views.admin_advisory_update,   name='admin_advisory_update'),
    path('admin/advisory/<int:pk>/approve/',  views.admin_advisory_approve,  name='admin_advisory_approve'),
    path('admin/advisory/<int:pk>/dispatch/', views.admin_advisory_dispatch, name='admin_advisory_dispatch'),
    path('admin/advisory/<int:pk>/delete/',   views.admin_advisory_delete,   name='admin_advisory_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Trials CRUD
    # ----------------------------------------------------------------
    path('admin/trial/add/',             views.admin_trial_create, name='admin_trial_create'),
    path('admin/trial/<int:pk>/edit/',   views.admin_trial_update, name='admin_trial_update'),
    path('admin/trial/<int:pk>/delete/', views.admin_trial_delete, name='admin_trial_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — PINN Models CRUD
    # ----------------------------------------------------------------
    path('admin/pinn/add/',             views.admin_pinn_create, name='admin_pinn_create'),
    path('admin/pinn/<int:pk>/edit/',   views.admin_pinn_update, name='admin_pinn_update'),
    path('admin/pinn/<int:pk>/delete/', views.admin_pinn_delete, name='admin_pinn_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Weather Records CRUD
    # ----------------------------------------------------------------
    path('admin/weather/add/',             views.admin_weather_create, name='admin_weather_create'),
    path('admin/weather/<int:pk>/edit/',   views.admin_weather_update, name='admin_weather_update'),
    path('admin/weather/<int:pk>/delete/', views.admin_weather_delete, name='admin_weather_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Soil Tests CRUD
    # ----------------------------------------------------------------
    path('admin/soil/add/',             views.admin_soil_create, name='admin_soil_create'),
    path('admin/soil/<int:pk>/edit/',   views.admin_soil_update, name='admin_soil_update'),
    path('admin/soil/<int:pk>/delete/', views.admin_soil_delete, name='admin_soil_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Crops CRUD
    # ----------------------------------------------------------------
    path('admin/crop/add/',             views.admin_crop_create, name='admin_crop_create'),
    path('admin/crop/<int:pk>/edit/',   views.admin_crop_update, name='admin_crop_update'),
    path('admin/crop/<int:pk>/delete/', views.admin_crop_delete, name='admin_crop_delete'),

    # ----------------------------------------------------------------
    # Admin dashboard — Integration configs CRUD
    # ----------------------------------------------------------------
    path('admin/integration/add/',             views.admin_integration_create, name='admin_integration_create'),
    path('admin/integration/<int:pk>/edit/',   views.admin_integration_update, name='admin_integration_update'),
    path('admin/integration/<int:pk>/delete/', views.admin_integration_delete, name='admin_integration_delete'),

    # ----------------------------------------------------------------
    # Advisory public CRUD
    # ----------------------------------------------------------------
    path('list/', views.AdvisoryListView.as_view(), name='advisory_list'),
    path('create/', views.AdvisoryCreateView.as_view(), name='advisory_create'),
    path('<int:pk>/', views.AdvisoryDetailView.as_view(), name='advisory_detail'),
    path('<int:pk>/edit/', views.AdvisoryUpdateView.as_view(), name='advisory_update'),
    path('<int:pk>/explanation/', views.AdvisoryExplanationView.as_view(), name='advisory_explanation'),
    path('<int:pk>/approve/', views.approve_advisory_view, name='advisory_approve'),
    path('<int:pk>/dispatch/', views.dispatch_advisory_view, name='advisory_dispatch'),
    path('<int:advisory_pk>/feedback/', views.submit_feedback_view, name='advisory_feedback_submit'),

    # Delivery & feedback
    path('deliveries/', views.AdvisoryDeliveryLogView.as_view(), name='advisory_delivery_log'),
    path('feedback/', views.AdvisoryFeedbackListView.as_view(), name='advisory_feedback_list'),

    # Generation
    path('generate/', views.generate_advisory_view, name='advisory_generate'),
    path('bulk-generate/', views.bulk_generate_advisories_view, name='advisory_bulk_generate'),
]