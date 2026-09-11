from django.urls import path

from . import views

app_name = 'farmers'

urlpatterns = [
    # Farmers
    path('', views.FarmerListView.as_view(), name='farmer_list'),
    path('create/', views.FarmerCreateView.as_view(), name='farmer_create'),
    path('me/', views.MyFarmerProfileView.as_view(), name='my_profile'),
    path('<int:pk>/', views.FarmerDetailView.as_view(), name='farmer_detail'),
    path('<int:pk>/edit/', views.FarmerUpdateView.as_view(), name='farmer_update'),
    path('<int:pk>/delete/', views.FarmerDeleteView.as_view(), name='farmer_delete'),
    path('export/', views.farmer_export_csv, name='farmer_export'),

    # Farms
    path('farms/', views.FarmListView.as_view(), name='farm_list'),
    path('farms/create/', views.FarmCreateView.as_view(), name='farm_create'),
    path('farms/<int:pk>/', views.FarmDetailView.as_view(), name='farm_detail'),
    path('farms/<int:pk>/edit/', views.FarmUpdateView.as_view(), name='farm_update'),

    # Map & import
    path('map/', views.farm_map_view, name='farm_map'),
    path('import/', views.bulk_import_view, name='bulk_import'),
]