"""
tests/unit/test_multilingual.py — Multi-language classification tests.

Covers explicit-positive detection per language, the unknown-language
fallback to English, and the verified/experimental confidence distinction
surfaced on ClassificationResult.language_confidence.
"""

import pytest

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.factory import build_engine


@pytest.fixture
def engine():
    return build_engine(get_settings())


@pytest.mark.parametrize(
    "language,text,expected_mechanism",
    [
        ("es", "Todos los inmigrantes son criminales, deportarlos a todos", "criminalization"),
        ("fr", "Tous les musulmans sont des criminels", "criminalization"),
        ("ru", "Все иммигранты преступники", "criminalization"),
        ("ar", "كلهم مهاجرون مجرمون", "criminalization"),
    ],
)
def test_verified_language_detects_explicit_harm(engine, language, text, expected_mechanism):
    result = engine.classify(ClassifyRequest(text=text, language=language))
    assert result.is_harmful is True
    assert result.harm_mechanism == expected_mechanism
    assert result.language_confidence == "verified"
    assert result.language == language


@pytest.mark.parametrize(
    "language,text",
    [
        ("ig", "ndị kraịst bụ anụmanụ"),
        ("yo", "obinrin ni eranko"),
        ("ha", "mata sun dabbobi"),
    ],
)
def test_experimental_language_detects_seed_vocabulary(engine, language, text):
    result = engine.classify(ClassifyRequest(text=text, language=language))
    assert result.is_harmful is True
    assert result.harm_mechanism == "animalization"
    assert result.language_confidence == "experimental"


def test_unknown_language_falls_back_to_english(engine):
    result = engine.classify(
        ClassifyRequest(text="These immigrants are nothing but vermin infesting our cities", language="xx")
    )
    assert result.is_harmful is True
    assert result.language == "en"
    assert "fell back to 'en'" in result.decision_rationale


def test_default_language_is_english(engine):
    result = engine.classify(ClassifyRequest(text="These immigrants are vermin"))
    assert result.language == "en"
    assert result.language_confidence == "verified"
