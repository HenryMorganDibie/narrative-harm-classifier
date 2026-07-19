"""narrative_harm_classifier — narrative harm classification, escalation tracking, and benchmarking."""

__version__ = "0.1.0"

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassificationResult, ClassifyRequest
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy

__all__ = [
    "__version__",
    "classify",
    "ClassificationResult",
    "ClassifyRequest",
    "ClassificationEngine",
]


def classify(text: str, context: str | None = None) -> ClassificationResult:
    """Convenience one-shot classification using the default taxonomy and settings."""
    settings = get_settings()
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    azure_client = AzureNLPClient(
        endpoint=settings.azure_text_analytics_endpoint,
        key=settings.azure_text_analytics_key,
    )
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=azure_client)
    return engine.classify(ClassifyRequest(text=text, context=context))
