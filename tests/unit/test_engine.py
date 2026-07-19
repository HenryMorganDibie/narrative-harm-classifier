"""
tests/unit/test_engine.py — Unit tests for classification engine.

Tests multi-signal logic, threshold decisions, ambiguity resolution,
and identity anchor detection without requiring Azure credentials.
"""

import pytest
from narrative_harm_classifier.core.models import ClassifyRequest, HarmCategory
from narrative_harm_classifier.core.config import Settings, get_settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine, _detect_identity_anchor, _detect_harm_signals
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient

TAXONOMY_PATH = get_settings().taxonomy_config_path


@pytest.fixture
def taxonomy():
    return load_taxonomy(TAXONOMY_PATH)


@pytest.fixture
def engine(taxonomy):
    azure = AzureNLPClient()  # fallback mode — no credentials needed
    return ClassificationEngine(taxonomy=taxonomy, azure_client=azure)


# --- Identity anchor detection ---

def test_detects_ethnic_group_anchor():
    axis = _detect_identity_anchor("Black people deserve equal rights")
    assert axis == "race_ethnicity"


def test_detects_religious_group_anchor():
    axis = _detect_identity_anchor("Muslim communities face discrimination")
    assert axis == "religion"


def test_detects_gender_anchor():
    axis = _detect_identity_anchor("Women should have equal pay")
    assert axis == "gender"


def test_no_anchor_returns_none():
    axis = _detect_identity_anchor("The weather is nice today")
    assert axis is None


# --- Harm pattern detection ---

def test_animalization_pattern():
    from narrative_harm_classifier.classifier.taxonomy.loader import TaxonomyRow
    row = TaxonomyRow(
        row_id="test", target_type="ethnic_group",
        harm_mechanism="animalization", identity_axis="race_ethnicity",
        signal_weight=0.9, decision_threshold=0.65
    )
    matched, pattern, match_obj, matched_text = _detect_harm_signals("they are vermin infesting our streets", row)
    assert matched is True
    assert pattern is not None
    assert match_obj is not None


def test_no_harm_pattern():
    from narrative_harm_classifier.classifier.taxonomy.loader import TaxonomyRow
    row = TaxonomyRow(
        row_id="test", target_type="ethnic_group",
        harm_mechanism="animalization", identity_axis="race_ethnicity",
        signal_weight=0.9, decision_threshold=0.65
    )
    matched, _, _, _ = _detect_harm_signals("I love animals and wildlife", row)
    assert matched is False


# --- Full classification ---

def test_dehumanization_detected(engine):
    req = ClassifyRequest(text="These immigrants are subhuman vermin that infest our cities")
    result = engine.classify(req)
    assert result.is_harmful is True
    assert result.harm_category == HarmCategory.DEHUMANIZATION


def test_benign_text_not_harmful(engine):
    req = ClassifyRequest(text="The documentary explored animal migration patterns in Africa")
    result = engine.classify(req)
    assert result.is_harmful is False
    assert result.harm_category == HarmCategory.NONE


def test_no_identity_anchor_returns_no_harm(engine):
    req = ClassifyRequest(text="They are vermin and cockroaches")  # no group identity
    result = engine.classify(req)
    assert result.is_harmful is False


def test_result_has_rationale(engine):
    req = ClassifyRequest(text="Muslim followers are demonic servants of evil")
    result = engine.classify(req)
    assert result.decision_rationale is not None
    assert len(result.decision_rationale) > 0


def test_result_has_taxonomy_version(engine):
    req = ClassifyRequest(text="Normal text here")
    result = engine.classify(req)
    assert result.taxonomy_version == "1.0.0"


def test_confidence_bounded(engine):
    req = ClassifyRequest(text="These subhuman animals must be eliminated from our country")
    result = engine.classify(req)
    assert 0.0 <= result.confidence <= 1.0


def test_batch_classify(engine):
    texts = [
        "Immigrants are vermin, subhuman beasts infesting our streets",
        "Immigration policy is a complex issue with many perspectives",
        "Women are just property that exist to serve men",
    ]
    results = [engine.classify(ClassifyRequest(text=t)) for t in texts]
    assert results[0].is_harmful is True
    assert results[1].is_harmful is False
    assert results[2].is_harmful is True
