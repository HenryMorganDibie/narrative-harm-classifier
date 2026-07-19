"""
api/routes/health.py
"""

from fastapi import APIRouter, Depends
from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "taxonomy_version": taxonomy.version,
        "taxonomy_baseline": taxonomy.baseline_tag,
        "priority_category": taxonomy.priority_category,
        "azure_configured": bool(settings.azure_text_analytics_endpoint),
    }
