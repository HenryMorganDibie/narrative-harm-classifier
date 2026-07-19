"""
tests/unit/test_counter_narrative.py — Counter-narrative guidance tests.
"""

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.factory import build_engine
from narrative_harm_classifier.classifier.counter_narrative import guidance_for


def test_guidance_for_known_mechanism():
    text = guidance_for("animalization")
    assert text is not None
    assert "dehumaniz" in text.lower()


def test_guidance_for_direct_call_to_violence_favors_escalation():
    text = guidance_for("direct_call_to_violence")
    assert "escalat" in text.lower() or "human review" in text.lower()


def test_guidance_for_none_mechanism_is_none():
    assert guidance_for(None) is None


def test_guidance_for_unknown_mechanism_returns_default():
    text = guidance_for("some_future_mechanism")
    assert text is not None


def test_harmful_classification_includes_guidance():
    engine = build_engine(get_settings())
    result = engine.classify(ClassifyRequest(text="These immigrants are nothing but vermin infesting our cities"))
    assert result.is_harmful is True
    assert result.counter_narrative_guidance is not None


def test_benign_classification_has_no_guidance():
    engine = build_engine(get_settings())
    result = engine.classify(ClassifyRequest(text="The weather is nice today"))
    assert result.is_harmful is False
    assert result.counter_narrative_guidance is None
