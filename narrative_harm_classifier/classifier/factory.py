"""
classifier/factory.py — Shared construction of engine/tracker/runner/validator.

Every API route and every CLI command previously rebuilt "load taxonomy +
build Azure client + build ClassificationEngine" independently (six
near-identical copies across api/routes/*.py and cli.py). Centralizing it
here means a change to how the engine is constructed (e.g. adding
dog-whistle lexicon loading) happens once.
"""

from narrative_harm_classifier.core.config import Settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy, TaxonomyConfig
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.rules.dogwhistles import load_dogwhistles, DogwhistleLexicon
from narrative_harm_classifier.classifier.tracking.store import get_store, TrackingStore
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker
from narrative_harm_classifier.classifier.validators.benchmark import BenchmarkRunner
from narrative_harm_classifier.classifier.validators.performance import PerformanceValidator


def build_taxonomy(settings: Settings) -> TaxonomyConfig:
    return load_taxonomy(settings.taxonomy_config_path)


def build_azure_client(settings: Settings) -> AzureNLPClient:
    return AzureNLPClient(
        endpoint=settings.azure_text_analytics_endpoint,
        key=settings.azure_text_analytics_key,
    )


def build_dogwhistle_lexicon(settings: Settings) -> DogwhistleLexicon:
    return load_dogwhistles(settings.dogwhistles_path)


def build_engine(settings: Settings) -> ClassificationEngine:
    return ClassificationEngine(
        taxonomy=build_taxonomy(settings),
        azure_client=build_azure_client(settings),
        patterns_dir=settings.patterns_dir,
        dogwhistles=build_dogwhistle_lexicon(settings),
    )


def build_tracker(settings: Settings) -> EscalationTracker:
    store: TrackingStore = get_store(settings.effective_tracking_db_url)
    return EscalationTracker(engine=build_engine(settings), store=store)


def build_benchmark_runner(settings: Settings) -> BenchmarkRunner:
    taxonomy = build_taxonomy(settings)
    return BenchmarkRunner(
        engine=build_engine(settings),
        taxonomy_version=taxonomy.version,
        templates_path=settings.benchmark_templates_path,
    )


def build_validator(settings: Settings) -> PerformanceValidator:
    return PerformanceValidator(engine=build_engine(settings), taxonomy=build_taxonomy(settings))
