from django.urls import path

from . import views

app_name = 'pinn_engine'

urlpatterns = [
    # Models
    path('', views.PINNModelListView.as_view(), name='model_list'),
    path('models/create/', views.PINNModelCreateView.as_view(), name='model_create'),
    path('models/<int:pk>/', views.PINNModelDetailView.as_view(), name='model_detail'),
    path('models/<int:pk>/edit/', views.PINNModelUpdateView.as_view(), name='model_update'),

    # Physics constraints
    path('physics/', views.PhysicsConstraintListView.as_view(), name='physics_constraint_list'),
    path('physics/create/', views.PhysicsConstraintCreateView.as_view(), name='physics_constraint_create'),
    path('physics/<int:pk>/edit/', views.PhysicsConstraintUpdateView.as_view(), name='physics_constraint_update'),

    # Training runs
    path('training/', views.TrainingRunListView.as_view(), name='trainingrun_list'),
    path('training/create/', views.TrainingRunCreateView.as_view(), name='trainingrun_create'),
    path('training/<int:pk>/', views.TrainingRunDetailView.as_view(), name='trainingrun_detail'),
    path('training/<int:pk>/logs/', views.TrainingRunLogsView.as_view(), name='trainingrun_logs'),

    # Inference
    path('inference/', views.InferenceListView.as_view(), name='inference_list'),
    path('inference/run/', views.inference_run_view, name='inference_run'),
    path('inference/<int:pk>/', views.InferenceDetailView.as_view(), name='inference_detail'),

    # Metrics dashboard
    path('metrics/', views.metrics_dashboard_view, name='metrics_dashboard'),

    # CSV import
    path('import/', views.csv_import_view, name='csv_import'),
]