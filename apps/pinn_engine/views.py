from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView,
)

from apps.accounts.permissions import (
    ResearcherRequired, KALROAdminRequired, researcher_required,
)
from apps.farmers.models import Farm
from apps.crops.models import Crop
from .forms import (
    PINNModelForm, PhysicsConstraintForm, TrainingRunForm,
    InferenceRunForm, ModelMetricFilterForm,
)
from .models import (
    PhysicsConstraint, PINNModel, TrainingRun, InferenceRun, ModelMetric,
)


# ==================================================================
# PINN MODELS
# ==================================================================
class PINNModelListView(ResearcherRequired, ListView):
    model = PINNModel
    template_name = 'pinn_engine/model_list.html'
    context_object_name = 'models'
    paginate_by = 30
    ordering = ['-updated_at']

    def get_queryset(self):
        qs = PINNModel.objects.annotate(
            constraint_count=Count('physics_constraints'),
            training_run_count=Count('training_runs'),
        )
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        arch = self.request.GET.get('architecture')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if arch:
            qs = qs.filter(architecture=arch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PINNModel.Status.choices
        ctx['architectures'] = PINNModel.Architecture.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('q', 'status', 'architecture')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class PINNModelDetailView(ResearcherRequired, DetailView):
    model = PINNModel
    template_name = 'pinn_engine/model_detail.html'
    context_object_name = 'model'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['constraints'] = self.object.physics_constraints.all()
        ctx['recent_runs'] = self.object.training_runs.all()[:10]
        ctx['recent_inferences'] = self.object.inference_runs.all()[:10]
        ctx['latest_metrics'] = self.object.metric_snapshots.all()[:20]
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class PINNModelCreateView(ResearcherRequired, CreateView):
    model = PINNModel
    form_class = PINNModelForm
    template_name = 'pinn_engine/model_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "PINN model created.")
        return super().form_valid(form)


class PINNModelUpdateView(ResearcherRequired, UpdateView):
    model = PINNModel
    form_class = PINNModelForm
    template_name = 'pinn_engine/model_form.html'

    def form_valid(self, form):
        messages.success(self.request, "PINN model updated.")
        return super().form_valid(form)


# ==================================================================
# PHYSICS CONSTRAINTS
# ==================================================================
class PhysicsConstraintListView(ResearcherRequired, ListView):
    model = PhysicsConstraint
    template_name = 'pinn_engine/physics_constraint_list.html'
    context_object_name = 'constraints'
    paginate_by = 40

    def get_queryset(self):
        qs = PhysicsConstraint.objects.select_related('crop')
        kind = self.request.GET.get('kind')
        domain = self.request.GET.get('domain')
        active = self.request.GET.get('active')
        if kind:
            qs = qs.filter(kind=kind)
        if domain:
            qs = qs.filter(domain=domain)
        if active == '1':
            qs = qs.filter(is_active=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kinds'] = PhysicsConstraint.Kind.choices
        ctx['domains'] = PhysicsConstraint.Domain.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('kind', 'domain', 'active')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class PhysicsConstraintCreateView(KALROAdminRequired, CreateView):
    model = PhysicsConstraint
    form_class = PhysicsConstraintForm
    template_name = 'pinn_engine/physics_constraint_form.html'
    success_url = reverse_lazy('pinn_engine:physics_constraint_list')

    def form_valid(self, form):
        messages.success(self.request, "Physics constraint created.")
        return super().form_valid(form)


class PhysicsConstraintUpdateView(KALROAdminRequired, UpdateView):
    model = PhysicsConstraint
    form_class = PhysicsConstraintForm
    template_name = 'pinn_engine/physics_constraint_form.html'
    success_url = reverse_lazy('pinn_engine:physics_constraint_list')

    def form_valid(self, form):
        messages.success(self.request, "Physics constraint updated.")
        return super().form_valid(form)


# ==================================================================
# TRAINING RUNS
# ==================================================================
class TrainingRunListView(ResearcherRequired, ListView):
    model = TrainingRun
    template_name = 'pinn_engine/trainingrun_list.html'
    context_object_name = 'runs'
    paginate_by = 40
    ordering = ['-created_at']

    def get_queryset(self):
        qs = TrainingRun.objects.select_related('model', 'triggered_by')
        model_id = self.request.GET.get('model')
        status = self.request.GET.get('status')
        if model_id:
            qs = qs.filter(model_id=model_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['models'] = PINNModel.objects.all()
        ctx['statuses'] = TrainingRun.Status.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('model', 'status')}
        ctx['can_edit'] = self.request.user.is_kalro_staff or self.request.user.is_researcher
        return ctx


class TrainingRunDetailView(ResearcherRequired, DetailView):
    model = TrainingRun
    template_name = 'pinn_engine/trainingrun_detail.html'
    context_object_name = 'run'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['metrics'] = self.object.metric_snapshots.order_by('epoch')[:200]
        ctx['inferences'] = self.object.inferences.all()[:10]
        return ctx


class TrainingRunCreateView(ResearcherRequired, CreateView):
    model = TrainingRun
    form_class = TrainingRunForm
    template_name = 'pinn_engine/trainingrun_form.html'

    def get_initial(self):
        initial = super().get_initial()
        model_id = self.request.GET.get('model')
        if model_id:
            initial['model'] = model_id
        return initial

    def form_valid(self, form):
        form.instance.triggered_by = self.request.user
        form.instance.status = TrainingRun.Status.QUEUED
        response = super().form_valid(form)
        try:
            from apps.integrations.tasks import train_pinn
            train_pinn.delay(self.object.pk)
        except Exception as e:
            self.object.status = TrainingRun.Status.FAILED
            self.object.error_text = str(e)
            self.object.save()
        messages.success(self.request, "Training run queued.")
        return response


class TrainingRunLogsView(ResearcherRequired, DetailView):
    model = TrainingRun
    template_name = 'pinn_engine/trainingrun_logs.html'
    context_object_name = 'run'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['logs'] = self.object.log_text.splitlines()
        ctx['loss_history'] = self.object.loss_history
        return ctx


# ==================================================================
# INFERENCE
# ==================================================================
class InferenceListView(ResearcherRequired, ListView):
    model = InferenceRun
    template_name = 'pinn_engine/inference_list.html'
    context_object_name = 'inferences'
    paginate_by = 40
    ordering = ['-created_at']

    def get_queryset(self):
        qs = InferenceRun.objects.select_related('model', 'farm', 'crop', 'requested_by')
        model_id = self.request.GET.get('model')
        status = self.request.GET.get('status')
        farm_id = self.request.GET.get('farm')
        if model_id:
            qs = qs.filter(model_id=model_id)
        if status:
            qs = qs.filter(status=status)
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['models'] = PINNModel.objects.filter(status=PINNModel.Status.READY)
        ctx['statuses'] = InferenceRun.Status.choices
        ctx['current'] = {k: self.request.GET.get(k, '') for k in ('model', 'status', 'farm')}
        return ctx


class InferenceDetailView(ResearcherRequired, DetailView):
    model = InferenceRun
    template_name = 'pinn_engine/inference_detail.html'
    context_object_name = 'inference'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fa = self.object.feature_attributions or {}
        ctx['attributions_sorted'] = sorted(
            fa.items(), key=lambda kv: abs(kv[1]), reverse=True,
        )[:15]
        ctx['residuals_sorted'] = sorted(
            (self.object.physics_residuals or {}).items(),
            key=lambda kv: abs(kv[1]), reverse=True,
        )
        return ctx


@researcher_required
def inference_run_view(request):
    if request.method == 'POST':
        form = InferenceRunForm(request.POST)
        if form.is_valid():
            inf = form.save(commit=False)
            inf.requested_by = request.user
            inf.status = InferenceRun.Status.QUEUED
            inf.input_payload = form.cleaned_data.get('override_payload') or {}
            inf.save()
            try:
                from apps.integrations.tasks import run_inference
                run_inference.delay(inf.pk)
                messages.info(request, f"Inference #{inf.pk} queued.")
            except Exception as e:
                inf.status = InferenceRun.Status.FAILED
                inf.error_text = str(e)
                inf.save()
                messages.error(request, f"Could not queue inference: {e}")
            return redirect('pinn_engine:inference_detail', pk=inf.pk)
    else:
        form = InferenceRunForm()

    return render(request, 'pinn_engine/inference_run.html', {'form': form})


# ==================================================================
# METRICS DASHBOARD
# ==================================================================
@researcher_required
def metrics_dashboard_view(request):
    model_id = request.GET.get('model')
    training_run_id = request.GET.get('training_run')

    models = PINNModel.objects.all()
    snapshots = ModelMetric.objects.all().order_by('epoch')

    if model_id:
        snapshots = snapshots.filter(model_id=model_id)
    if training_run_id:
        snapshots = snapshots.filter(training_run_id=training_run_id)

    epochs, data_loss, physics_loss, total_loss, rmse, r2 = [], [], [], [], [], []
    for s in snapshots[:500]:
        epochs.append(s.epoch)
        data_loss.append(float(s.data_loss or 0))
        physics_loss.append(float(s.physics_loss or 0))
        total_loss.append(float(s.total_loss or 0))
        rmse.append(float(s.rmse or 0))
        r2.append(float(s.r2 or 0))

    aggregate = ModelMetric.objects.aggregate(
        avg_rmse=Avg('rmse'),
        avg_r2=Avg('r2'),
        best_r2=Max('r2'),
        worst_r2=Min('r2'),
    )

    return render(request, 'pinn_engine/metrics_dashboard.html', {
        'models': models,
        'current_model': model_id or '',
        'current_run': training_run_id or '',
        'epochs': epochs,
        'data_loss': data_loss,
        'physics_loss': physics_loss,
        'total_loss': total_loss,
        'rmse': rmse,
        'r2': r2,
        'aggregate': aggregate,
        'total_snapshots': snapshots.count(),
    })


# ==================================================================
# CSV BULK IMPORT
# ==================================================================
@researcher_required
def csv_import_view(request):
    """
    Upload a CSV file and import it into one of the supported models.
    Delegates to integrations.tasks.import_csv_batch.
    """
    import os
    import tempfile

    if request.method == 'POST':
        model_name = request.POST.get('model_name', '').strip()
        uploaded_file = request.FILES.get('csv_file')

        if not model_name:
            messages.error(request, "Please select a target model.")
            return redirect('pinn_engine:csv_import')

        if not uploaded_file:
            messages.error(request, "Please attach a CSV file.")
            return redirect('pinn_engine:csv_import')

        # Persist to a temp file so the async task can read it
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix='.csv', prefix=f'kalro_import_{model_name}_',
        )
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp.close()

        try:
            from apps.integrations.tasks import import_csv_batch
            result = import_csv_batch(
                model_name=model_name,
                file_path=tmp.name,
                user_id=request.user.pk,
            )
            messages.success(
                request,
                f"Import complete — {result['imported']} imported, "
                f"{result['failed']} failed of {result['total_rows']} rows.",
            )
            if result['failed']:
                # Show the first 5 errors as warnings
                for err in result['errors'][:5]:
                    messages.warning(request, err)
        except Exception as e:
            messages.error(request, f"Import failed: {e}")
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        return redirect('pinn_engine:csv_import')

    # GET — show the upload form
    from apps.integrations.tasks import csv_import_mappings
    supported = list(csv_import_mappings().keys())
    recent_metrics = ModelMetric.objects.select_related('model').order_by('-recorded_at')[:10]

    return render(request, 'pinn_engine/csv_import.html', {
        'supported_models': supported,
        'recent_metrics': recent_metrics,
    })

# ==================================================================
# DIAGNOSTIC
# ==================================================================
@researcher_required
def pinn_diagnostics_view(request):
    """
    Shows the current state of PINN models, artifacts, and torch
    availability. Used for debugging on Render.
    """
    import os
    import sys

    # --- Torch check ---
    torch_status = {'available': False, 'error': None, 'version': None}
    try:
        import torch
        torch_status['available'] = True
        torch_status['version'] = torch.__version__
    except Exception as e:
        torch_status['error'] = f"{type(e).__name__}: {e}"

    # --- Model inventory ---
    models = []
    for m in PINNModel.objects.all():
        artifact_exists = False
        artifact_size = None
        if m.artifact_path:
            try:
                artifact_exists = os.path.exists(m.artifact_path)
                if artifact_exists:
                    artifact_size = os.path.getsize(m.artifact_path)
            except Exception:
                artifact_exists = False
        models.append({
            'obj': m,
            'status': m.status,
            'artifact_path': m.artifact_path or '—',
            'artifact_exists': artifact_exists,
            'artifact_size': artifact_size,
            'n_inputs': len(m.input_features or []),
            'n_outputs': len(m.output_targets or []),
            'n_constraints': m.physics_constraints.count(),
        })

    # --- Inference inventory ---
    inferences = InferenceRun.objects.select_related('model').order_by('-created_at')[:10]

    # --- Environment ---
    env = {
        'DEBUG': os.environ.get('DEBUG', 'not set'),
        'PYTHON_VERSION': sys.version.split()[0],
        'PLATFORM': sys.platform,
        'WORKING_DIR': os.getcwd(),
        'TMP_EXISTS': os.path.exists('/tmp'),
        'TMP_WRITABLE': False,
    }
    if env['TMP_EXISTS']:
        try:
            with open('/tmp/kalro_test.txt', 'w') as f:
                f.write('test')
            os.unlink('/tmp/kalro_test.txt')
            env['TMP_WRITABLE'] = True
        except Exception:
            pass

    return render(request, 'pinn_engine/diagnostics.html', {
        'torch_status': torch_status,
        'models': models,
        'inferences': inferences,
        'env': env,
    })
