from django.urls import path

from . import views

app_name = 'soil'

urlpatterns = [
    # Soil tests
    path('', views.SoilTestListView.as_view(), name='soiltest_list'),
    path('tests/create/', views.SoilTestCreateView.as_view(), name='soiltest_create'),
    path('tests/<int:pk>/', views.SoilTestDetailView.as_view(), name='soiltest_detail'),
    path('tests/<int:pk>/edit/', views.SoilTestUpdateView.as_view(), name='soiltest_update'),

    # Nutrient profiles
    path('nutrient-profiles/', views.NutrientProfileListView.as_view(), name='nutrient_profile'),
    path('nutrient-profiles/create/', views.NutrientProfileCreateView.as_view(), name='nutrient_profile_create'),
    path('nutrient-profiles/<int:pk>/edit/', views.NutrientProfileUpdateView.as_view(), name='nutrient_profile_update'),

    # Market prices
    path('market-prices/', views.MarketPriceListView.as_view(), name='marketprice_list'),
    path('market-prices/create/', views.MarketPriceCreateView.as_view(), name='marketprice_create'),
    path('market-prices/<int:pk>/edit/', views.MarketPriceUpdateView.as_view(), name='marketprice_update'),

    # Sync
    path('sync/agdata/', views.sync_agdata_view, name='sync_agdata'),
]