"""
tests/unit/test_provenance.py — Content hashing and hash-chain tamper detection.
"""

import pytest
from datetime import datetime

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.factory import build_engine
from narrative_harm_classifier.classifier.provenance import GENESIS_HASH, content_hash, record_hash
from narrative_harm_classifier.classifier.tracking.store import TrackingStore
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker


def test_content_hash_is_deterministic():
    h1 = content_hash("some text", "some context", "1.0.0")
    h2 = content_hash("some text", "some context", "1.0.0")
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex digest


def test_content_hash_differs_for_different_input():
    h1 = content_hash("text A", None, "1.0.0")
    h2 = content_hash("text B", None, "1.0.0")
    assert h1 != h2


def test_classification_result_has_content_hash():
    engine = build_engine(get_settings())
    result = engine.classify(ClassifyRequest(text="Some text to classify"))
    assert len(result.content_hash) == 64
    assert result.content_hash == content_hash("Some text to classify", None, result.taxonomy_version)


@pytest.fixture
def tracker(tmp_path):
    store = TrackingStore(f"sqlite:///{tmp_path}/provenance_test.db")
    engine = build_engine(get_settings())
    return EscalationTracker(engine=engine, store=store)


def test_first_observation_chains_to_genesis(tracker):
    obs = tracker.observe("source-a", ClassifyRequest(text="Immigration policy is a complex issue"))
    assert obs.prev_hash == GENESIS_HASH
    expected = record_hash(
        prev_hash=GENESIS_HASH,
        source_id="source-a",
        text_excerpt=obs.text_excerpt,
        is_harmful=obs.is_harmful,
        harm_mechanism=obs.harm_mechanism,
        confidence=obs.confidence,
        observed_at=obs.observed_at,
        content_hash_value=obs.content_hash,
    )
    assert obs.record_hash == expected


def test_chain_verifies_intact_on_untouched_history(tracker):
    for text in ["Immigration policy is a complex issue", "All immigrants are criminals, deport them all"]:
        tracker.observe("source-b", ClassifyRequest(text=text))

    result = tracker.verify_chain("source-b")
    assert result.intact is True
    assert result.observation_count == 2


def test_chain_detects_tampering(tracker):
    for text in [
        "Immigration policy is a complex issue",
        "All immigrants are criminals, deport them all",
        "We must attack immigrants and eliminate them",
    ]:
        tracker.observe("source-c", ClassifyRequest(text=text))

    # Tamper with the first record directly in the store, bypassing the API.
    from narrative_harm_classifier.classifier.tracking.store import observations_table
    from sqlalchemy import update

    with tracker.store.engine.begin() as conn:
        conn.execute(
            update(observations_table)
            .where(observations_table.c.source_id == "source-c")
            .where(observations_table.c.id == 1)
            .values(text_excerpt="TAMPERED TEXT")
        )

    result = tracker.verify_chain("source-c")
    assert result.intact is False
    assert result.first_broken_id == 1


def test_verify_chain_on_empty_history_is_intact(tracker):
    result = tracker.verify_chain("never-observed-source")
    assert result.observation_count == 0
    assert result.intact is True
