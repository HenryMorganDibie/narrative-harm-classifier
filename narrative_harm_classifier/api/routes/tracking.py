"""
api/routes/tracking.py — Escalation-chain tracking endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.factory import build_tracker
from narrative_harm_classifier.classifier.tracking.models import SourceProfile, Observation, ChainVerification
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker

router = APIRouter()


def get_tracker(settings: Settings = Depends(get_settings)) -> EscalationTracker:
    return build_tracker(settings)


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


@router.get(
    "/{source_id}/verify",
    response_model=ChainVerification,
    summary="Verify the tamper-evident hash chain for a source's observation history",
    description=(
        "Recomputes the hash chain over the full stored history and confirms it's intact. "
        "Detects tampering with any historical record; does not prevent it."
    ),
)
def verify_chain(
    source_id: str,
    tracker: EscalationTracker = Depends(get_tracker),
) -> ChainVerification:
    result = tracker.verify_chain(source_id)
    if result.observation_count == 0:
        raise HTTPException(status_code=404, detail=f"No observations recorded for source '{source_id}'")
    return result
