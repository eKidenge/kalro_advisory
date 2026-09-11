import csv
import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from apps.accounts.permissions import (
    KALROAdminRequired, ResearcherRequired, researcher_required,
)
from apps.farmers.models import County
from apps.crops.models import Crop
from .forms import TrialForm, TrialResultForm, TrialImportForm
from .models import (
    TrialSite, Trial, TrialTreatment, TrialResult, TrialImportBatch,
)


# ==================================================================
# TRIALS
# ==================================================================
class TrialListView(ResearcherRequired, ListView):
    model = Trial
    template_name = 'trials/trial_list.html'
    context_object_name = 'trials'
    paginate_by = 40
    ordering = ['-started_on', '-created_at']

    def get_queryset(self):
        qs = Trial.objects.select_related('site', 'crop', 'county', 'lead_researcher')
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        crop = self.request.GET.get('crop')
        county = self.request.GET.get('county')
        published = self.request.GET.get('published')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if crop:
            qs = qs.filter(crop_id=crop)
        if county:
            qs = qs.filter(county_id=county)
        if published == '1':
            qs = qs.filter(is_published=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Trial.Status.choices
        ctx['crops'] = Crop.objects.all()
        ctx['counties'] = County.objects.all()
        ctx['current'] = {k: self.request.GET.get(k, '') for k in
                          ('q', 'status', 'crop', 'county', 'published')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        ctx['can_delete'] = self.request.user.is_kalro_staff
        return ctx


class TrialDetailView(ResearcherRequired, DetailView):
    model = Trial
    template_name = 'trials/trial_detail.html'
    context_object_name = 'trial'

    def get_queryset(self):
        return Trial.objects.select_related(
            'site', 'crop', 'county', 'lead_researcher',
        ).prefetch_related('treatments')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        ctx['can_delete'] = self.request.user.is_kalro_staff
        return ctx


class TrialCreateView(ResearcherRequired, CreateView):
    model = Trial
    form_class = TrialForm
    template_name = 'trials/trial_form.html'

    def form_valid(self, form):
        if not form.instance.lead_researcher:
            form.instance.lead_researcher = self.request.user
        messages.success(self.request, "Trial created.")
        return super().form_valid(form)


class TrialUpdateView(ResearcherRequired, UpdateView):
    model = Trial
    form_class = TrialForm
    template_name = 'trials/trial_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Trial updated.")
        return super().form_valid(form)


class TrialDeleteView(KALROAdminRequired, DeleteView):
    model = Trial
    template_name = 'trials/trial_confirm_delete.html'
    success_url = reverse_lazy('trials:trial_list')

    def form_valid(self, form):
        messages.success(self.request, "Trial deleted.")
        return super().form_valid(form)


# ==================================================================
# TRIAL RESULTS
# ==================================================================
class TrialResultListView(ResearcherRequired, ListView):
    model = TrialResult
    template_name = 'trials/trial_result_list.html'
    context_object_name = 'results'
    paginate_by = 60
    ordering = ['-observed_on']

    def get_queryset(self):
        qs = TrialResult.objects.select_related('treatment', 'treatment__trial')
        trial = self.request.GET.get('trial')
        treatment = self.request.GET.get('treatment')
        if trial:
            qs = qs.filter(treatment__trial_id=trial)
        if treatment:
            qs = qs.filter(treatment_id=treatment)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['trials'] = Trial.objects.all()
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('trial', 'treatment')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class TrialResultCreateView(ResearcherRequired, CreateView):
    model = TrialResult
    form_class = TrialResultForm
    template_name = 'trials/trial_result_form.html'

    def get_initial(self):
        initial = super().get_initial()
        treatment_id = self.request.GET.get('treatment')
        if treatment_id:
            initial['treatment'] = treatment_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Result recorded.")
        return super().form_valid(form)


class TrialResultUpdateView(ResearcherRequired, UpdateView):
    model = TrialResult
    form_class = TrialResultForm
    template_name = 'trials/trial_result_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Result updated.")
        return super().form_valid(form)


# ==================================================================
# ANALYTICS
# ==================================================================
class TrialAnalyticsView(ResearcherRequired, ListView):
    model = Trial
    template_name = 'trials/trial_analytics.html'
    context_object_name = 'trials'
    paginate_by = 30

    def get_queryset(self):
        return Trial.objects.select_related('crop', 'county').filter(
            is_published=True,
        ).order_by('-started_on')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        trial_id = self.request.GET.get('trial')
        summary = []
        queryset = Trial.objects.filter(is_published=True)
        if trial_id:
            queryset = queryset.filter(pk=trial_id)
        for t in queryset[:20]:
            per_treatment = (
                TrialResult.objects
                .filter(treatment__trial=t)
                .values('treatment__code', 'treatment__name', 'treatment__is_control')
                .annotate(
                    avg_yield=Avg('grain_yield_kg_ha'),
                    avg_biomass=Avg('biomass_kg_ha'),
                    avg_nue=Avg('nitrogen_use_efficiency'),
                    n=Count('id'),
                )
                .order_by('-avg_yield')
            )
            summary.append({'trial': t, 'treatments': list(per_treatment)})
        ctx['summary'] = summary
        ctx['all_trials'] = Trial.objects.filter(is_published=True)
        ctx['current_trial'] = trial_id or ''
        return ctx


# ==================================================================
# IMPORT (researcher + admin)
# ==================================================================
@researcher_required
def trial_import_view(request):
    if request.method == 'POST':
        form = TrialImportForm(request.POST, request.FILES)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.uploaded_by = request.user
            batch.status = TrialImportBatch.Status.RUNNING
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
                    trial = batch.trial or Trial.objects.get(code=row['trial_code'].strip())
                    treatment, _ = TrialTreatment.objects.get_or_create(
                        trial=trial,
                        code=row['treatment_code'].strip(),
                        defaults={
                            'name': row.get('treatment_name', '').strip()
                                    or row['treatment_code'].strip(),
                        },
                    )

                    def dec(k):
                        v = row.get(k, '').strip()
                        return Decimal(v) if v else None

                    TrialResult.objects.create(
                        treatment=treatment,
                        plot_number=row.get('plot_number', '').strip(),
                        replication=int(row['replication']) if row.get('replication') else None,
                        observed_on=row['observed_on'].strip(),
                        plant_height_cm=dec('plant_height_cm'),
                        biomass_kg_ha=dec('biomass_kg_ha'),
                        grain_yield_kg_ha=dec('grain_yield_kg_ha'),
                        total_yield_kg_ha=dec('total_yield_kg_ha'),
                        soil_ph=dec('soil_ph'),
                        soil_n_pct=dec('soil_n_pct'),
                        soil_p_ppm=dec('soil_p_ppm'),
                        soil_k_ppm=dec('soil_k_ppm'),
                        nitrogen_use_efficiency=dec('nitrogen_use_efficiency'),
                        rainfall_mm=dec('rainfall_mm'),
                        source_row=row,
                    )
                    imported += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {i}: {e}")

            batch.imported_count = imported
            batch.failed_count = failed
            batch.error_log = '\n'.join(errors)
            batch.status = (
                TrialImportBatch.Status.SUCCESS if failed == 0
                else TrialImportBatch.Status.PARTIAL if imported > 0
                else TrialImportBatch.Status.FAILED
            )
            batch.finished_at = timezone.now()
            batch.save()

            messages.success(request, f"Imported {imported} results, {failed} failed.")
            return redirect('trials:trial_list')
    else:
        form = TrialImportForm()

    recent = TrialImportBatch.objects.all()[:10]
    return render(request, 'trials/trial_import.html', {'form': form, 'recent': recent})


# ==================================================================
# CSV EXPORT
# ==================================================================
@login_required
def trial_result_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="trial_results.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'trial_code', 'treatment_code', 'plot_number', 'replication',
        'observed_on', 'plant_height_cm', 'biomass_kg_ha',
        'grain_yield_kg_ha', 'total_yield_kg_ha',
        'soil_ph', 'soil_n_pct', 'soil_p_ppm', 'soil_k_ppm',
        'nitrogen_use_efficiency', 'rainfall_mm',
    ])
    qs = TrialResult.objects.select_related('treatment', 'treatment__trial')
    trial_id = request.GET.get('trial')
    if trial_id:
        qs = qs.filter(treatment__trial_id=trial_id)
    for r in qs:
        writer.writerow([
            r.treatment.trial.code, r.treatment.code, r.plot_number, r.replication,
            r.observed_on, r.plant_height_cm, r.biomass_kg_ha,
            r.grain_yield_kg_ha, r.total_yield_kg_ha,
            r.soil_ph, r.soil_n_pct, r.soil_p_ppm, r.soil_k_ppm,
            r.nitrogen_use_efficiency, r.rainfall_mm,
        ])
    return response


# ==================================================================
# TRIAL SITES
# ==================================================================
class TrialSiteDetailView(ResearcherRequired, DetailView):
    model = TrialSite
    template_name = 'trials/trial_detail.html'
    context_object_name = 'site'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['trials'] = self.object.trials.all()[:20]
        ctx['is_site'] = True
        return ctx