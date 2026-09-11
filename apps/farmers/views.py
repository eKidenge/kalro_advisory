import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from apps.accounts.permissions import (
    KALROStaffRequired, KALROAdminRequired, FarmerAccess, kalro_admin_required,
)
from .forms import FarmerForm, FarmForm, FarmerImportForm
from .models import Farmer, Farm, County, FarmerImportBatch


# ==================================================================
# SCOPING HELPERS
# ==================================================================
def _scope_farmers_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(county__name__iexact=user.county)
    if user.is_farmer:
        return qs.filter(user=user)
    return qs.none()


def _scope_farms_for(user, qs):
    if user.is_superuser or user.is_kalro_staff or user.is_researcher:
        return qs
    if user.is_field_agent and user.county:
        return qs.filter(county__name__iexact=user.county)
    if user.is_farmer:
        return qs.filter(farmer__user=user)
    return qs.none()


# ==================================================================
# FARMER VIEWS
# ==================================================================
class FarmerListView(KALROStaffRequired, ListView):
    model = Farmer
    template_name = 'farmers/farmer_list.html'
    context_object_name = 'farmers'
    paginate_by = 40
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Farmer.objects.select_related('county', 'user').annotate(
            farms_total=Count('farms'),
        )
        qs = _scope_farmers_for(self.request.user, qs)

        q = self.request.GET.get('q')
        county = self.request.GET.get('county')
        enterprise = self.request.GET.get('enterprise')
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(national_id__icontains=q) |
                Q(phone_number__icontains=q)
            )
        if county:
            qs = qs.filter(county_id=county)
        if enterprise:
            qs = qs.filter(primary_enterprise__icontains=enterprise)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_field_agent and self.request.user.county:
            ctx['counties'] = County.objects.filter(name__iexact=self.request.user.county)
        else:
            ctx['counties'] = County.objects.all()
        ctx['current_q'] = self.request.GET.get('q', '')
        ctx['current_county'] = self.request.GET.get('county', '')
        ctx['current_enterprise'] = self.request.GET.get('enterprise', '')
        ctx['total_count'] = self.get_queryset().count()
        ctx['is_county_scoped'] = self.request.user.is_field_agent
        return ctx


class FarmerDetailView(KALROStaffRequired, DetailView):
    model = Farmer
    template_name = 'farmers/farmer_detail.html'
    context_object_name = 'farmer'

    def get_queryset(self):
        qs = Farmer.objects.select_related('county', 'user')
        return _scope_farmers_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['farms'] = self.object.farms.select_related('county')
        ctx['advisories'] = (
            self.object.advisories.select_related('farm')[:10]
            if hasattr(self.object, 'advisories') else []
        )
        return ctx


class FarmerCreateView(KALROStaffRequired, CreateView):
    model = Farmer
    form_class = FarmerForm
    template_name = 'farmers/farmer_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        if self.request.user.is_field_agent and self.request.user.county:
            form.instance.county = County.objects.filter(
                name__iexact=self.request.user.county
            ).first()
        messages.success(self.request, "Farmer registered successfully.")
        return super().form_valid(form)


class FarmerUpdateView(KALROStaffRequired, UpdateView):
    model = Farmer
    form_class = FarmerForm
    template_name = 'farmers/farmer_form.html'

    def get_queryset(self):
        qs = Farmer.objects.all()
        return _scope_farmers_for(self.request.user, qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Farmer updated.")
        return super().form_valid(form)


class FarmerDeleteView(KALROAdminRequired, DeleteView):
    model = Farmer
    template_name = 'farmers/farmer_confirm_delete.html'
    success_url = reverse_lazy('farmers:farmer_list')

    def form_valid(self, form):
        messages.success(self.request, "Farmer deleted.")
        return super().form_valid(form)


# ==================================================================
# MY PROFILE (farmer sees own record)
# ==================================================================
class MyFarmerProfileView(FarmerAccess, DetailView):
    template_name = 'farmers/farmer_detail.html'
    context_object_name = 'farmer'

    def get_object(self):
        farmer = getattr(self.request.user, 'farmer_profile', None)
        if farmer is None:
            messages.info(self.request, "You don't have a farmer profile yet.")
            return None
        return farmer

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return redirect('advisories:advisory_dashboard')
        context = self.get_context_data(object=self.object)
        context['is_self_view'] = True
        return self.render_to_response(context)


# ==================================================================
# FARM VIEWS
# ==================================================================
class FarmListView(KALROStaffRequired, ListView):
    model = Farm
    template_name = 'farmers/farm_list.html'
    context_object_name = 'farms'
    paginate_by = 40
    ordering = ['farmer', 'name']

    def get_queryset(self):
        qs = Farm.objects.select_related('farmer', 'county')
        qs = _scope_farms_for(self.request.user, qs)

        county = self.request.GET.get('county')
        irrigation = self.request.GET.get('irrigation')
        if county:
            qs = qs.filter(county_id=county)
        if irrigation:
            qs = qs.filter(irrigation_type=irrigation)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_field_agent and self.request.user.county:
            ctx['counties'] = County.objects.filter(name__iexact=self.request.user.county)
        else:
            ctx['counties'] = County.objects.all()
        ctx['irrigation_types'] = Farm.IrrigationType.choices
        return ctx


class FarmDetailView(KALROStaffRequired, DetailView):
    model = Farm
    template_name = 'farmers/farm_detail.html'
    context_object_name = 'farm'

    def get_queryset(self):
        qs = Farm.objects.select_related('farmer', 'county')
        return _scope_farms_for(self.request.user, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['soil_tests'] = (
            self.object.soil_tests.all()[:10]
            if hasattr(self.object, 'soil_tests') else []
        )
        ctx['weather_records'] = (
            self.object.weather_records.all()[:10]
            if hasattr(self.object, 'weather_records') else []
        )
        return ctx


class FarmCreateView(KALROStaffRequired, CreateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farmers/farm_form.html'

    def get_initial(self):
        initial = super().get_initial()
        farmer_id = self.request.GET.get('farmer')
        if farmer_id:
            initial['farmer'] = farmer_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Farm added.")
        return super().form_valid(form)


class FarmUpdateView(KALROStaffRequired, UpdateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farmers/farm_form.html'

    def get_queryset(self):
        qs = Farm.objects.all()
        return _scope_farms_for(self.request.user, qs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Farm updated.")
        return super().form_valid(form)


# ==================================================================
# MAP
# ==================================================================
@login_required
def farm_map_view(request):
    farms = Farm.objects.select_related('farmer', 'county').filter(
        gps_latitude__isnull=False,
        gps_longitude__isnull=False,
    )
    farms = _scope_farms_for(request.user, farms)

    county_id = request.GET.get('county')
    if county_id:
        farms = farms.filter(county_id=county_id)

    points = [
        {
            'id': f.pk,
            'name': f.name,
            'farmer': f.farmer.full_name,
            'county': f.county.name if f.county else '',
            'lat': float(f.gps_latitude),
            'lng': float(f.gps_longitude),
            'url': f.get_absolute_url(),
        }
        for f in farms
    ]

    if request.user.is_field_agent and request.user.county:
        counties = County.objects.filter(name__iexact=request.user.county)
    else:
        counties = County.objects.all()

    return render(request, 'farmers/farm_map.html', {
        'points': points,
        'counties': counties,
    })


# ==================================================================
# BULK IMPORT (KALRO admin only)
# ==================================================================
@kalro_admin_required
def bulk_import_view(request):
    if request.method == 'POST':
        form = FarmerImportForm(request.POST, request.FILES)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.uploaded_by = request.user
            batch.status = FarmerImportBatch.Status.RUNNING
            batch.started_at = timezone.now()
            batch.save()

            decoded = batch.file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)
            batch.total_rows = len(rows)

            imported = failed = 0
            errors = []

            for i, row in enumerate(rows, start=1):
                try:
                    county_name = row.get('county', '').strip()
                    county = County.objects.filter(name__iexact=county_name).first()
                    Farmer.objects.update_or_create(
                        national_id=row['national_id'].strip(),
                        defaults={
                            'full_name': row.get('full_name', '').strip(),
                            'phone_number': row.get('phone_number', '').strip(),
                            'email': row.get('email', '').strip(),
                            'county': county,
                            'sub_county': row.get('sub_county', '').strip(),
                            'ward': row.get('ward', '').strip(),
                            'village': row.get('village', '').strip(),
                            'primary_enterprise': row.get('primary_enterprise', '').strip(),
                            'registration_source': 'BULK_IMPORT',
                            'registered_by': request.user,
                        },
                    )
                    imported += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {i}: {e}")

            batch.imported_count = imported
            batch.failed_count = failed
            batch.error_log = '\n'.join(errors)
            batch.status = (
                FarmerImportBatch.Status.SUCCESS if failed == 0
                else FarmerImportBatch.Status.PARTIAL if imported > 0
                else FarmerImportBatch.Status.FAILED
            )
            batch.finished_at = timezone.now()
            batch.save()

            messages.success(request, f"Imported {imported} farmers, {failed} failed.")
            return redirect('farmers:farmer_list')
    else:
        form = FarmerImportForm()

    recent = FarmerImportBatch.objects.all()[:10]
    return render(request, 'farmers/bulk_import.html', {'form': form, 'recent': recent})


# ==================================================================
# CSV EXPORT (scoped)
# ==================================================================
@login_required
def farmer_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="farmers.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'national_id', 'full_name', 'gender', 'phone_number', 'email',
        'county', 'sub_county', 'ward', 'village',
        'total_land_size', 'land_size_unit', 'primary_enterprise',
    ])

    qs = Farmer.objects.select_related('county').all()
    qs = _scope_farmers_for(request.user, qs)

    for f in qs:
        writer.writerow([
            f.national_id, f.full_name, f.gender, f.phone_number, f.email,
            f.county.name if f.county else '', f.sub_county, f.ward, f.village,
            f.total_land_size, f.land_size_unit, f.primary_enterprise,
        ])
    return response