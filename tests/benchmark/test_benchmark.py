"""
tests/benchmark/test_benchmark.py — Structural tests + hard gate for the templated benchmark suite.

The engine handles negation, counter-speech, obfuscated spelling, and
cross-group consistency via explainable heuristics (see CONTRIBUTING.md for
how, and their limits). These assertions are a real regression gate: a PR
that breaks one of those heuristics, or the underlying patterns, fails CI.
"""

import pytest

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.validators.benchmark import (
    generate_benchmark_cases,
    BenchmarkRunner,
)

EXPECTED_TEST_TYPES = {
    "explicit_positive",
    "implicit_positive",
    "negation",
    "counter_speech",
    "obfuscated_spelling",
    "benign_trigger_word",
}


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def runner(settings):
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=AzureNLPClient())
    return BenchmarkRunner(
        engine=engine,
        taxonomy_version=taxonomy.version,
        templates_path=settings.benchmark_templates_path,
    )


def test_generates_a_substantial_case_set(settings):
    cases = generate_benchmark_cases(settings.benchmark_templates_path)
    # Far more than the old 18 hand-picked samples, and generated systematically.
    assert len(cases) >= 150

    case_ids = [c.case_id for c in cases]
    assert len(case_ids) == len(set(case_ids)), "case_ids must be unique"


def test_all_expected_test_types_present(settings):
    cases = generate_benchmark_cases(settings.benchmark_templates_path)
    test_types = {c.test_type for c in cases}
    assert EXPECTED_TEST_TYPES.issubset(test_types)


def test_report_structure_is_well_formed(runner):
    report = runner.run()

    assert report.sample_count >= 150
    assert report.overall.sample_count == report.sample_count

    reported_test_types = {t.test_type for t in report.by_test_type}
    assert EXPECTED_TEST_TYPES.issubset(reported_test_types)

    for t in report.by_test_type:
        assert 0.0 <= t.precision <= 1.0
        assert 0.0 <= t.recall <= 1.0
        assert 0.0 <= t.fpr <= 1.0

    # Every group-expanded template should have a consistency entry
    assert len(report.group_consistency) > 0
    for entry in report.group_consistency:
        assert len(entry.verdicts) == 6  # one per group in benchmark_templates.yaml


def test_overall_benchmark_is_clean(runner):
    """
    Hard gate: overall precision/recall must be perfect and FPR zero on the
    current benchmark suite. This does NOT mean evasion is a solved problem in
    general — it means this specific, versioned test suite passes cleanly, so
    a future PR that regresses it (or weakens a heuristic) gets caught here
    instead of silently shipping.
    """
    report = runner.run()
    assert report.overall.precision == 1.0
    assert report.overall.recall == 1.0
    assert report.overall.fpr == 0.0


@pytest.mark.parametrize(
    "test_type",
    ["explicit_positive", "implicit_positive", "obfuscated_spelling"],
)
def test_positive_test_types_are_fully_caught(runner, test_type):
    report = runner.run()
    t = next(t for t in report.by_test_type if t.test_type == test_type)
    assert t.recall == 1.0
    assert t.precision == 1.0


@pytest.mark.parametrize(
    "test_type",
    ["negation", "counter_speech", "benign_trigger_word"],
)
def test_negative_test_types_have_zero_false_positive_rate(runner, test_type):
    """
    These test types are entirely hard negatives (expected_is_harmful=False),
    so precision/recall are undefined (no positives exist) — FPR is the
    metric that actually measures whether the engine over-fires on them.
    """
    report = runner.run()
    t = next(t for t in report.by_test_type if t.test_type == test_type)
    assert t.fpr == 0.0


def test_cross_group_consistency_is_complete(runner):
    """
    Every group-expanded template must produce the same verdict regardless of
    which identity group was slotted in (this caught a real plural-form bug
    in the political_affiliation identity anchors — see CONTRIBUTING.md).
    """
    report = runner.run()
    inconsistent = [g for g in report.group_consistency if not g.consistent]
    assert inconsistent == []
