"""
tests/benchmark/test_benchmark.py — Structural tests for the templated benchmark suite.

These deliberately do NOT assert specific pass thresholds: the current
regex-based engine is known to be weak on negation, counter-speech, and
obfuscated spelling (see CONTRIBUTING.md). Those numbers are the new honest
baseline surfaced in `nhc benchmark run`, not a gate to force green.
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
        assert len(entry.verdicts) == 5  # one per group in benchmark_templates.yaml


def test_explicit_positive_cases_are_mostly_caught(runner):
    """
    Sanity floor: the 'easy' explicit positive cases (the kind of language the
    original 18-sample set was built from) should still be caught well above
    chance. This is NOT true of negation/counter_speech/obfuscated_spelling —
    those are documented known gaps, not asserted here.
    """
    report = runner.run()
    explicit = next(t for t in report.by_test_type if t.test_type == "explicit_positive")
    assert explicit.recall >= 0.7
