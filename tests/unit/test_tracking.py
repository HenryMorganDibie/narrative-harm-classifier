"""
tests/unit/test_tracking.py — Escalation-chain tracking tests.

Tests severity mapping, trend computation (escalating/stable/de-escalating),
and persistence round-trip using a throwaway in-memory-per-test SQLite file
(each test gets its own store keyed by tmp_path, so tests can't interfere).
"""

import pytest

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.tracking.models import (
    SeverityLevel,
    severity_for_mechanism,
    risk_level_for,
)
from narrative_harm_classifier.classifier.tracking.store import TrackingStore
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker


@pytest.fixture
def engine():
    settings = get_settings()
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    return ClassificationEngine(taxonomy=taxonomy, azure_client=AzureNLPClient())


@pytest.fixture
def tracker(engine, tmp_path):
    store = TrackingStore(f"sqlite:///{tmp_path}/tracking_test.db")
    return EscalationTracker(engine=engine, store=store)


# --- Severity mapping ---

def test_no_harm_maps_to_none_severity():
    assert severity_for_mechanism(None) == SeverityLevel.NONE


def test_direct_call_to_violence_is_highest_severity():
    assert severity_for_mechanism("direct_call_to_violence") == SeverityLevel.DIRECT_VIOLENCE_CALL


def test_false_attribution_is_lowest_nonzero_severity():
    assert severity_for_mechanism("false_attribution") == SeverityLevel.NARRATIVE_DISTORTION


# --- Risk level mapping ---

def test_risk_level_escalates_one_step_on_escalating_trend():
    stable_risk = risk_level_for(SeverityLevel.NARRATIVE_DISTORTION, "stable")
    escalating_risk = risk_level_for(SeverityLevel.NARRATIVE_DISTORTION, "escalating")
    levels = ("low", "watch", "elevated", "critical")
    assert levels.index(escalating_risk) == levels.index(stable_risk) + 1


def test_risk_level_caps_at_critical():
    assert risk_level_for(SeverityLevel.DIRECT_VIOLENCE_CALL, "escalating") == "critical"


# --- Tracker: persistence + profile ---

def test_observe_persists_and_profile_reflects_it(tracker):
    tracker.observe("source-a", ClassifyRequest(text="Immigration policy is a divisive issue"))
    profile = tracker.profile("source-a")
    assert profile.observation_count == 1
    assert profile.current_severity == SeverityLevel.NONE


def test_profile_with_no_observations_is_insufficient_data(tracker):
    profile = tracker.profile("nonexistent-source")
    assert profile.observation_count == 0
    assert profile.trend == "insufficient_data"
    assert profile.risk_level == "low"


def test_escalating_sequence_is_detected(tracker):
    source = "escalating-source"
    texts = [
        "Immigration policy is a complex issue",  # none
        "Immigration policy is a complex issue",  # none
        "All immigrants are criminals and rapists, deport them all",  # criminalization
        "We must attack immigrants and eliminate them from our society",  # direct_call_to_violence
    ]
    for text in texts:
        tracker.observe(source, ClassifyRequest(text=text))

    profile = tracker.profile(source)
    assert profile.observation_count == 4
    assert profile.trend == "escalating"
    assert profile.risk_level in ("elevated", "critical")


def test_stable_benign_sequence_is_not_escalating(tracker):
    source = "stable-source"
    texts = [
        "Crime statistics vary across demographic groups",
        "The documentary explored animal migration patterns",
        "Feminist scholars have written on objectification theory",
        "Political opinion pieces often provoke strong reactions",
    ]
    for text in texts:
        tracker.observe(source, ClassifyRequest(text=text))

    profile = tracker.profile(source)
    assert profile.trend == "stable"
    assert profile.risk_level == "low"


def test_list_profiles_sorts_by_risk(tracker):
    tracker.observe("low-risk", ClassifyRequest(text="The weather is nice today"))
    tracker.observe(
        "high-risk",
        ClassifyRequest(text="We must attack immigrants and eliminate them from our society"),
    )

    profiles = tracker.list_profiles()
    assert profiles[0].source_id == "high-risk"
