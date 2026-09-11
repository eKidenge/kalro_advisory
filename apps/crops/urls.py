from django.urls import path

from . import views

app_name = 'crops'

urlpatterns = [
    # Crops
    path('', views.CropListView.as_view(), name='crop_list'),
    path('create/', views.CropCreateView.as_view(), name='crop_create'),
    path('<int:pk>/', views.CropDetailView.as_view(), name='crop_detail'),
    path('<int:pk>/edit/', views.CropUpdateView.as_view(), name='crop_update'),
    path('<int:pk>/requirements/', views.CropRequirementsView.as_view(), name='crop_requirements'),

    # Growth stages
    path('growth-stages/', views.GrowthStageListView.as_view(), name='growthstage_list'),
    path('growth-stages/create/', views.GrowthStageCreateView.as_view(), name='growthstage_create'),
    path('growth-stages/<int:pk>/edit/', views.GrowthStageUpdateView.as_view(), name='growthstage_update'),

    # Calendar
    path('calendar/', views.CropCalendarView.as_view(), name='crop_calendar'),
    path('calendar/create/', views.CropCalendarCreateView.as_view(), name='crop_calendar_create'),
    path('calendar/<int:pk>/edit/', views.CropCalendarUpdateView.as_view(), name='crop_calendar_update'),
]