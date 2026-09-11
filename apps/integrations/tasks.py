"""
Background tasks for external integrations and PINN operations.

Uses Celery when available; degrades gracefully to synchronous execution
with a warning when Celery is not configured. All tasks create SyncLog
records so admins can audit runs from /admin/ and the integration dashboards.
"""
from __future__ import annotations

import logging
import time

from django.utils import timezone

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Lazy Celery import — works even if Celery is not installed yet
# ------------------------------------------------------------------
try:
    from celery import shared_task
    _HAS_CELERY = True
except ImportError:
    _HAS_CELERY = False

    def shared_task(*args, **kwargs):
        def decorator(fn):
            fn.delay = lambda *a, **kw: fn(*a, **kw)   # sync fallback
            return fn
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


# ==================================================================
# KAOP — weather + forecast pull
# ==================================================================
@shared_task(name='integrations.sync_kaop')
def sync_kaop(log_id: int | None = None):
    """Pull weather + forecasts from KAOP into climate.WeatherRecord/Forecast."""
    from apps.climate.models import KAOPSyncLog, WeatherRecord, WeatherStation
    from .models import IntegrationConfig, SyncLog

    log = KAOPSyncLog.objects.filter(pk=log_id).first()
    if log is None:
        log = KAOPSyncLog.objects.create(status=KAOPSyncLog.Status.RUNNING)

    config = IntegrationConfig.objects.filter(
        provider=IntegrationConfig.Provider.KAOP, is_active=True,
    ).first()

    sync_log = SyncLog.objects.create(
        config=config,
        provider=IntegrationConfig.Provider.KAOP,
        operation=SyncLog.Operation.PULL_WEATHER,
        status=SyncLog.Status.RUNNING,
        triggered_by=log.triggered_by,
    )

    start = time.monotonic()
    try:
        if config is None:
            raise RuntimeError("No active KAOP integration config.")

        # Real HTTP client goes here — placeholder for now.
        # import requests
        # resp = requests.get(f"{config.base_url}/weather", headers=..., timeout=30)
        # resp.raise_for_status()
        # payload = resp.json()

        # Simulated no-op
        payload = {'records': []}

        fetched = len(payload.get('records', []))
        sync_log.records_fetched = fetched
        sync_log.status = SyncLog.Status.SUCCESS
        sync_log.response_summary = {'fetched': fetched}

        log.records_fetched = fetched
        log.status = KAOPSyncLog.Status.SUCCESS
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        logger.exception("KAOP sync failed: %s", e)
        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_text = str(e)
        log.status = KAOPSyncLog.Status.FAILED
        log.error_log = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise

    finally:
        sync_log.duration_ms = int((time.monotonic() - start) * 1000)
        sync_log.finished_at = timezone.now()
        sync_log.save()

    return sync_log.pk


# ==================================================================
# AgData Hub — soil + market pull
# ==================================================================
@shared_task(name='integrations.sync_agdata')
def sync_agdata(log_id: int | None = None):
    """Pull soil + market data from AgData Hub."""
    from apps.soil.models import AgDataSyncLog, SoilTest, MarketPrice
    from .models import IntegrationConfig, SyncLog

    log = AgDataSyncLog.objects.filter(pk=log_id).first()
    if log is None:
        log = AgDataSyncLog.objects.create(status=AgDataSyncLog.Status.RUNNING)

    config = IntegrationConfig.objects.filter(
        provider=IntegrationConfig.Provider.AGDATA, is_active=True,
    ).first()

    sync_log = SyncLog.objects.create(
        config=config,
        provider=IntegrationConfig.Provider.AGDATA,
        operation=SyncLog.Operation.PULL_SOIL,
        status=SyncLog.Status.RUNNING,
        triggered_by=log.triggered_by,
    )

    start = time.monotonic()
    try:
        if config is None:
            raise RuntimeError("No active AgData Hub config.")

        # Placeholder — real HTTP call goes here
        soil_payload = {'records': []}
        price_payload = {'records': []}

        sync_log.records_fetched = (
            len(soil_payload.get('records', [])) +
            len(price_payload.get('records', []))
        )
        sync_log.status = SyncLog.Status.SUCCESS

        log.soil_records_fetched = len(soil_payload.get('records', []))
        log.price_records_fetched = len(price_payload.get('records', []))
        log.status = AgDataSyncLog.Status.SUCCESS
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        logger.exception("AgData sync failed: %s", e)
        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_text = str(e)
        log.status = AgDataSyncLog.Status.FAILED
        log.error_log = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise

    finally:
        sync_log.duration_ms = int((time.monotonic() - start) * 1000)
        sync_log.finished_at = timezone.now()
        sync_log.save()

    return sync_log.pk


# ==================================================================
# PINN — training
# ==================================================================
@shared_task(name='integrations.train_pinn')
def train_pinn(training_run_id: int):
    """Execute PINN training for a TrainingRun."""
    from apps.pinn_engine.models import TrainingRun, ModelMetric

    run = TrainingRun.objects.filter(pk=training_run_id).first()
    if run is None:
        logger.warning("TrainingRun %s not found.", training_run_id)
        return None

    run.status = TrainingRun.Status.RUNNING
    run.started_at = timezone.now()
    run.log_text = "Training started…\n"
    run.save()

    start = time.monotonic()
    try:
        # Real training loop goes here — placeholder logs a few epochs.
        for epoch in range(1, min(run.epochs, 5) + 1):
            ModelMetric.objects.create(
                model=run.model,
                training_run=run,
                epoch=epoch,
                data_loss=1.0 / epoch,
                physics_loss=0.5 / epoch,
                total_loss=1.5 / epoch,
                rmse=1.0 / epoch,
                r2=1 - (1.0 / epoch),
                physics_residual=0.01 / epoch,
            )
            run.log_text += f"Epoch {epoch}: loss={1.5/epoch:.4f}\n"
            run.save(update_fields=['log_text'])

        run.status = TrainingRun.Status.SUCCESS
        run.final_metrics = {
            'rmse': 0.2, 'r2': 0.8, 'physics_residual': 0.002,
        }
        run.log_text += "Training complete.\n"

    except Exception as e:
        logger.exception("PINN training failed: %s", e)
        run.status = TrainingRun.Status.FAILED
        run.error_text = str(e)

    finally:
        run.finished_at = timezone.now()
        run.duration_seconds = int(time.monotonic() - start)
        run.save()

    return run.pk


# ==================================================================
# PINN — inference
# ==================================================================
@shared_task(name='integrations.run_inference')
def run_inference(inference_run_id: int):
    """Execute PINN inference for an InferenceRun."""
    from apps.pinn_engine.models import InferenceRun

    inf = InferenceRun.objects.filter(pk=inference_run_id).first()
    if inf is None:
        logger.warning("InferenceRun %s not found.", inference_run_id)
        return None

    start = time.monotonic()
    try:
        # Placeholder output
        inf.output_payload = {
            'recommended_n_kg_ha': 60,
            'recommended_p_kg_ha': 30,
            'recommended_k_kg_ha': 20,
            'expected_yield_kg_ha': 2800,
        }
        inf.feature_attributions = {
            'rainfall': 0.42,
            'soil_n': 0.31,
            'soil_p': 0.15,
            'temperature': 0.12,
        }
        inf.physics_residuals = {
            'water_balance': 0.008,
            'nutrient_cycle': 0.014,
            'energy_conservation': 0.003,
        }
        inf.status = InferenceRun.Status.SUCCESS
        inf.duration_ms = int((time.monotonic() - start) * 1000)
        inf.save()

    except Exception as e:
        logger.exception("Inference failed: %s", e)
        inf.status = InferenceRun.Status.FAILED
        inf.error_text = str(e)
        inf.duration_ms = int((time.monotonic() - start) * 1000)
        inf.save()
        raise

    return inf.pk


# ==================================================================
# Advisories — generation
# ==================================================================
@shared_task(name='integrations.generate_advisory')
def generate_advisory(advisory_id: int):
    """Populate a draft advisory using PINN inference + explainability."""
    from apps.advisories.models import Advisory
    from apps.pinn_engine.models import PINNModel, InferenceRun

    adv = Advisory.objects.filter(pk=advisory_id).first()
    if adv is None:
        logger.warning("Advisory %s not found.", advisory_id)
        return None

    try:
        ready_model = PINNModel.objects.filter(
            status=PINNModel.Status.READY,
        ).first()

        inf = InferenceRun.objects.create(
            model=ready_model,
            farm=adv.farm,
            crop=adv.crop,
            status=InferenceRun.Status.QUEUED,
            input_payload={
                'advisory_id': adv.pk,
                'kind': adv.kind,
                'priority': adv.priority,
            },
        )
        run_inference(inf.pk)

        out = inf.output_payload or {}
        adv.inference_run = inf
        adv.body = (
            f"Recommended N: {out.get('recommended_n_kg_ha', 'N/A')} kg/ha; "
            f"P: {out.get('recommended_p_kg_ha', 'N/A')} kg/ha; "
            f"K: {out.get('recommended_k_kg_ha', 'N/A')} kg/ha. "
            f"Expected yield: {out.get('expected_yield_kg_ha', 'N/A')} kg/ha."
        )
        adv.short_message = adv.body[:300]
        adv.explanation = (
            "Generated by the Physics-Informed Neural Network. "
            "Top contributing factors: rainfall, soil nitrogen, soil phosphorus."
        )
        adv.explanation_factors = [
            {'name': k, 'weight': v}
            for k, v in (inf.feature_attributions or {}).items()
        ]
        adv.physics_residuals = inf.physics_residuals or {}
        adv.save()

    except Exception as e:
        logger.exception("Advisory generation failed: %s", e)
        adv.body = f"Generation failed: {e}"
        adv.status = Advisory.Status.FAILED
        adv.save()
        raise

    return adv.pk


@shared_task(name='integrations.bulk_generate_advisories')
def bulk_generate_advisories(county_id: int, crop_id: int, kind: str):
    """Batch advisory generation for all drafts in a county/crop."""
    from apps.advisories.models import Advisory

    drafts = Advisory.objects.filter(
        status=Advisory.Status.DRAFT,
        farm__county_id=county_id,
        crop_id=crop_id,
        kind=kind,
    )
    for adv in drafts:
        try:
            generate_advisory(adv.pk)
        except Exception as e:
            logger.exception("Bulk generation failed for advisory %s: %s", adv.pk, e)
    return drafts.count()


# ==================================================================
# Advisories — dispatch
# ==================================================================
@shared_task(name='integrations.dispatch_advisory')
def dispatch_advisory(advisory_id: int):
    """
    Send an advisory to the farmer via SMS (iShamba) + Selector Platform.
    Creates AdvisoryDelivery rows for each channel.
    """
    from apps.advisories.models import Advisory, AdvisoryDelivery

    adv = Advisory.objects.filter(pk=advisory_id).first()
    if adv is None:
        logger.warning("Advisory %s not found.", advisory_id)
        return None

    phone = ''
    if adv.farmer:
        phone = adv.farmer.phone_number or ''
    elif adv.farm and adv.farm.farmer:
        phone = adv.farm.farmer.phone_number or ''

    created = []
    for channel in (AdvisoryDelivery.Channel.SMS, AdvisoryDelivery.Channel.SELECTOR):
        delivery = AdvisoryDelivery.objects.create(
            advisory=adv,
            channel=channel,
            status=AdvisoryDelivery.Status.QUEUED,
            recipient_phone=phone,
        )

        # Real HTTP push goes here — placeholder marks as SENT.
        try:
            # import requests
            # resp = requests.post(...)
            delivery.status = AdvisoryDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.provider_message_id = f"SIM-{delivery.pk}"
            delivery.save()
        except Exception as e:
            delivery.status = AdvisoryDelivery.Status.FAILED
            delivery.error_text = str(e)
            delivery.save()

        created.append(delivery.pk)

    adv.status = Advisory.Status.SENT
    adv.save(update_fields=['status'])

    return created


# ==================================================================
# Health check
# ==================================================================
@shared_task(name='integrations.health_check')
def health_check(provider: str):
    """Ping a provider and update IntegrationConfig health fields."""
    from .models import IntegrationConfig, SyncLog

    config = IntegrationConfig.objects.filter(provider=provider).first()
    if config is None:
        return None

    sync_log = SyncLog.objects.create(
        config=config,
        provider=provider,
        operation=SyncLog.Operation.HEALTH_CHECK,
        status=SyncLog.Status.RUNNING,
    )

    start = time.monotonic()
    try:
        if not config.base_url:
            raise RuntimeError("No base URL configured.")
        # Real ping goes here
        sync_log.status = SyncLog.Status.SUCCESS
        config.last_ok_at = timezone.now()
        config.last_error = ''
    except Exception as e:
        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_text = str(e)
        config.last_error = str(e)
    finally:
        config.last_check_at = timezone.now()
        config.save()
        sync_log.duration_ms = int((time.monotonic() - start) * 1000)
        sync_log.finished_at = timezone.now()
        sync_log.save()

    return sync_log.pk