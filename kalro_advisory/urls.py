"""
URL configuration for kalro_advisory project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views


urlpatterns = [
    # ----------------------------------------------------------------
    # Public pages (no auth required)
    # ----------------------------------------------------------------
    path('', views.landing_view, name='landing'),
    path('features/', views.features_view, name='features'),
    path('how-it-works/', views.how_it_works_view, name='how_it_works'),

    # ----------------------------------------------------------------
    # Admin
    # ----------------------------------------------------------------
    path('admin/', admin.site.urls),

    # ----------------------------------------------------------------
    # App URLconfs
    # ----------------------------------------------------------------
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('farmers/', include('apps.farmers.urls', namespace='farmers')),
    path('climate/', include('apps.climate.urls', namespace='climate')),
    path('soil/', include('apps.soil.urls', namespace='soil')),
    path('crops/', include('apps.crops.urls', namespace='crops')),
    path('trials/', include('apps.trials.urls', namespace='trials')),
    path('pinn/', include('apps.pinn_engine.urls', namespace='pinn_engine')),
    path('advisories/', include('apps.advisories.urls', namespace='advisories')),
    path('integrations/', include('apps.integrations.urls', namespace='integrations')),
]


# ------------------------------------------------------------------
# Error handlers (custom templates)
# ------------------------------------------------------------------
handler403 = 'kalro_advisory.views.handler403'
handler404 = 'kalro_advisory.views.handler404'
handler500 = 'kalro_advisory.views.handler500'


# ------------------------------------------------------------------
# Static & media (dev only)
# ------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)