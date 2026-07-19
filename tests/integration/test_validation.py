"""
tests/integration/test_validation.py — Phase 1 end-to-end validation test.

Runs the dehumanization category against the held-out sample set and
asserts that performance thresholds are met:
  Precision ≥ 0.70 | Recall ≥ 0.65 | FPR ≤ 0.20
"""

import pytest
from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.validators.performance import (
    PerformanceValidator,
    DEHUMANIZATION_VALIDATION_SAMPLES,
)

TAXONOMY_PATH = get_settings().taxonomy_config_path


@pytest.fixture
def validator():
    taxonomy = load_taxonomy(TAXONOMY_PATH)
    azure = AzureNLPClient()  # fallback mode
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=azure)
    return PerformanceValidator(engine=engine, taxonomy=taxonomy)


def test_dehumanization_end_to_end_validation(validator):
    """
    Phase 1 milestone gate: validates the priority taxonomy category
    end-to-end against held-out samples.
    """
    report = validator.validate_category(
        category_name="dehumanization",
        samples=DEHUMANIZATION_VALIDATION_SAMPLES,
    )

    print(f"\n{'='*50}")
    print(f"PHASE 1 VALIDATION REPORT — dehumanization")
    print(f"Taxonomy version: {report.taxonomy_version}")
    print(f"Samples: {report.sample_count}")
    print(f"TP={report.true_positives} FP={report.false_positives} "
          f"TN={report.true_negatives} FN={report.false_negatives}")
    print(f"Precision: {report.precision:.3f} (min: 0.70) {'✓' if report.meets_precision_threshold else '✗'}")
    print(f"Recall:    {report.recall:.3f} (min: 0.65) {'✓' if report.meets_recall_threshold else '✗'}")
    print(f"FPR:       {report.fpr:.3f} (max: 0.20) {'✓' if report.meets_fpr_threshold else '✗'}")
    print(f"F1:        {report.f1:.3f}")
    print(f"RESULT:    {'PASS ✓' if report.passes else 'FAIL ✗'}")
    print(f"{'='*50}")

    assert report.sample_count == len(DEHUMANIZATION_VALIDATION_SAMPLES)
    assert report.meets_precision_threshold, f"Precision {report.precision:.3f} < 0.70"
    assert report.meets_recall_threshold, f"Recall {report.recall:.3f} < 0.65"
    assert report.meets_fpr_threshold, f"FPR {report.fpr:.3f} > 0.20"
    assert report.passes
