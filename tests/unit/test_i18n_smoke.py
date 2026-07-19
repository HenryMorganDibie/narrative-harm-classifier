"""
tests/unit/test_i18n_smoke.py — Runs the per-language smoke test suite.

Not a full replication of the English 192-case benchmark (see
data/i18n_smoke_tests.yaml for why) — a floor confirming basic detection
works per language, including the experimental-tier ones.
"""

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.classifier.factory import build_engine
from narrative_harm_classifier.classifier.validators.i18n_smoke import run_i18n_smoke


def test_all_i18n_smoke_cases_pass():
    settings = get_settings()
    engine = build_engine(settings)
    report = run_i18n_smoke(engine, settings.i18n_smoke_tests_path)

    assert report.failed_cases == []
    assert report.passed == report.total


def test_i18n_smoke_covers_all_seven_non_english_languages():
    settings = get_settings()
    engine = build_engine(settings)
    report = run_i18n_smoke(engine, settings.i18n_smoke_tests_path)

    assert set(report.by_language.keys()) == {"es", "fr", "ru", "ar", "ig", "yo", "ha"}
