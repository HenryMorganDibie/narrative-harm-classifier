"""
api/routes/tracking.py — Escalation-chain tracking endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.tracking.models import SourceProfile, Observation
from narrative_harm_classifier.classifier.tracking.store import get_store
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker

router = APIRouter()


def get_tracker(settings: Settings = Depends(get_settings)) -> EscalationTracker:
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    azure_client = AzureNLPClient(
        endpoint=settings.azure_text_analytics_endpoint,
        key=settings.azure_text_analytics_key,
    )
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=azure_client)
    store = get_store(settings.effective_tracking_db_url)
    return EscalationTracker(engine=engine, store=store)


@router.post(
    "/{source_id}/observe",
    response_model=Observation,
    summary="Classify a text and record it against a tracked source",
    description=(
        "Classifies the text and appends it to the source's observation history, "
        "used to compute escalation trend and risk level over time."
    ),
)
def observe(
    source_id: str,
    request: ClassifyRequest,
    tracker: EscalationTracker = Depends(get_tracker),
) -> Observation:
    return tracker.observe(source_id, request)


@router.get(
    "/{source_id}",
    response_model=SourceProfile,
    summary="Get a tracked source's escalation profile",
)
def get_profile(
    source_id: str,
    window: int = 20,
    tracker: EscalationTracker = Depends(get_tracker),
) -> SourceProfile:
    profile = tracker.profile(source_id, window=window)
    if profile.observation_count == 0:
        raise HTTPException(status_code=404, detail=f"No observations recorded for source '{source_id}'")
    return profile


@router.get(
    "",
    response_model=list[SourceProfile],
    summary="List all tracked sources, sorted by risk (highest first)",
)
def list_profiles(
    window: int = 20,
    tracker: EscalationTracker = Depends(get_tracker),
) -> list[SourceProfile]:
    return tracker.list_profiles(window=window)
