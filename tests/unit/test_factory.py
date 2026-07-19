"""
tests/unit/test_factory.py — Shared construction helpers.

Light coverage: mainly guards against the six duplicated wiring blocks this
module replaced silently drifting back apart.
"""

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.classifier.factory import (
    build_engine,
    build_tracker,
    build_benchmark_runner,
    build_validator,
)
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker


def test_build_engine_returns_working_engine():
    engine = build_engine(get_settings())
    assert isinstance(engine, ClassificationEngine)
    assert engine.dogwhistles is not None


def test_build_tracker_returns_working_tracker():
    tracker = build_tracker(get_settings())
    assert isinstance(tracker, EscalationTracker)


def test_build_benchmark_runner_and_validator_construct_without_error():
    settings = get_settings()
    assert build_benchmark_runner(settings) is not None
    assert build_validator(settings) is not None
