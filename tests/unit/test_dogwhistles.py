"""
tests/unit/test_dogwhistles.py — Dog-whistle lexicon detection tests.
"""

import pytest

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.factory import build_engine, build_dogwhistle_lexicon


@pytest.fixture
def lexicon():
    return build_dogwhistle_lexicon(get_settings())


@pytest.fixture
def engine():
    return build_engine(get_settings())


def test_lexicon_loads_seed_entries(lexicon):
    terms = {e.term for e in lexicon.entries}
    assert "globalist" in terms
    assert "1488" in terms
    assert len(lexicon.entries) >= 10


def test_lexicon_detects_term_in_text(lexicon):
    matches = lexicon.detect("Jewish bankers are the real globalist puppet masters")
    assert any(m.term == "globalist" for m in matches)


def test_lexicon_no_match_on_unrelated_text(lexicon):
    matches = lexicon.detect("The weather is nice today")
    assert matches == []


def test_dogwhistle_contributes_signal_when_identity_anchor_present(engine):
    result = engine.classify(
        ClassifyRequest(text="Jewish bankers are the real globalist puppet masters controlling everything")
    )
    assert result.is_harmful is True
    assert result.dogwhistle_matched == "globalist"
    assert result.harm_mechanism == "false_attribution"


def test_dogwhistle_requires_identity_anchor(engine):
    """
    A dog-whistle term alone, with no identity anchor present, should not
    fire — the same require_target_present gate applies to every signal.
    """
    result = engine.classify(ClassifyRequest(text="The globalist economy affects everyone"))
    assert result.is_harmful is False


def test_unambiguous_term_has_higher_weight_than_ambiguous_term(lexicon):
    globalist = next(e for e in lexicon.entries if e.term == "globalist")
    day_of_the_rope = next(e for e in lexicon.entries if e.term == "day of the rope")
    assert day_of_the_rope.signal_weight > globalist.signal_weight
