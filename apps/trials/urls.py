from django.urls import path

from . import views

app_name = 'trials'

urlpatterns = [
    # Trials
    path('', views.TrialListView.as_view(), name='trial_list'),
    path('create/', views.TrialCreateView.as_view(), name='trial_create'),
    path('<int:pk>/', views.TrialDetailView.as_view(), name='trial_detail'),
    path('<int:pk>/edit/', views.TrialUpdateView.as_view(), name='trial_update'),
    path('<int:pk>/delete/', views.TrialDeleteView.as_view(), name='trial_delete'),

    # Trial sites
    path('sites/<int:pk>/', views.TrialSiteDetailView.as_view(), name='trial_site_detail'),

    # Results
    path('results/', views.TrialResultListView.as_view(), name='trial_result_list'),
    path('results/create/', views.TrialResultCreateView.as_view(), name='trial_result_create'),
    path('results/<int:pk>/edit/', views.TrialResultUpdateView.as_view(), name='trial_result_update'),
    path('results/export/', views.trial_result_export_csv, name='trial_result_export'),

    # Analytics & import
    path('analytics/', views.TrialAnalyticsView.as_view(), name='trial_analytics'),
    path('import/', views.trial_import_view, name='trial_import'),
]