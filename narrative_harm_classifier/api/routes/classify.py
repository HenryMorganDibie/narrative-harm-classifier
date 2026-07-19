"""
api/routes/classify.py — Classification endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from narrative_harm_classifier.core.models import ClassifyRequest, ClassificationResult, BatchClassifyRequest, BatchClassificationResult
from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.factory import build_engine
from datetime import datetime

router = APIRouter()


def get_engine(settings: Settings = Depends(get_settings)) -> ClassificationEngine:
    return build_engine(settings)


@router.post(
    "/",
    response_model=ClassificationResult,
    summary="Classify a single text item",
    description=(
        "Runs multi-dimensional classification against the active taxonomy. "
        "Returns harm category, confidence, matched signals, and decision rationale."
    ),
)
def classify_text(
    request: ClassifyRequest,
    engine: ClassificationEngine = Depends(get_engine),
) -> ClassificationResult:
    try:
        return engine.classify(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch",
    response_model=BatchClassificationResult,
    summary="Classify a batch of text items (max 100)",
)
def classify_batch(
    request: BatchClassifyRequest,
    engine: ClassificationEngine = Depends(get_engine),
) -> BatchClassificationResult:
    results = [engine.classify(item) for item in request.items]
    harmful = sum(1 for r in results if r.is_harmful)
    settings = get_settings()
    taxonomy = load_taxonomy(settings.taxonomy_config_path)

    return BatchClassificationResult(
        results=results,
        total=len(results),
        harmful_count=harmful,
        taxonomy_version=taxonomy.version,
        processed_at=datetime.utcnow(),
    )
