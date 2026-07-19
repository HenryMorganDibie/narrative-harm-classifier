"""
api/routes/validate.py — Validation endpoints.
Runs held-out sample validation and returns performance reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from narrative_harm_classifier.core.models import ValidationSample, ValidationReport
from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.validators.performance import (
    PerformanceValidator,
    DEHUMANIZATION_VALIDATION_SAMPLES,
)

router = APIRouter()


def get_validator(settings: Settings = Depends(get_settings)) -> PerformanceValidator:
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    azure_client = AzureNLPClient(
        endpoint=settings.azure_text_analytics_endpoint,
        key=settings.azure_text_analytics_key,
    )
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=azure_client)
    return PerformanceValidator(engine=engine, taxonomy=taxonomy)


@router.post(
    "/dehumanization",
    response_model=ValidationReport,
    summary="Run Phase 1 end-to-end validation for priority category: dehumanization",
    description=(
        "Validates the dehumanization category against the built-in held-out sample set. "
        "Checks Precision ≥ 0.70, Recall ≥ 0.65, FPR ≤ 0.20. "
        "This is the Phase 1 milestone validation gate."
    ),
)
def validate_dehumanization(
    validator: PerformanceValidator = Depends(get_validator),
) -> ValidationReport:
    try:
        return validator.validate_category(
            category_name="dehumanization",
            samples=DEHUMANIZATION_VALIDATION_SAMPLES,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/custom",
    response_model=ValidationReport,
    summary="Run validation against a custom sample set",
)
def validate_custom(
    category: str,
    samples: list[ValidationSample],
    validator: PerformanceValidator = Depends(get_validator),
) -> ValidationReport:
    if not samples:
        raise HTTPException(status_code=400, detail="At least one sample required")
    try:
        return validator.validate_category(category_name=category, samples=samples)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
