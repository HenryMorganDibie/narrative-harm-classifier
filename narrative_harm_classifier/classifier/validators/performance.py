"""
classifier/validators/performance.py — Classification performance validator.

Runs held-out sample validation against configured thresholds:
  - Precision ≥ 0.70
  - Recall ≥ 0.65
  - FPR ≤ 0.20

Generates structured ValidationReport for each taxonomy category.
Used for Phase 1 end-to-end validation and M1 baseline establishment.
"""

import logging
from datetime import datetime

from narrative_harm_classifier.core.models import ClassifyRequest, ValidationSample, ValidationReport
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.taxonomy.loader import TaxonomyConfig

logger = logging.getLogger(__name__)


class PerformanceValidator:

    def __init__(self, engine: ClassificationEngine, taxonomy: TaxonomyConfig):
        self.engine = engine
        self.taxonomy = taxonomy

    def validate_category(
        self,
        category_name: str,
        samples: list[ValidationSample],
    ) -> ValidationReport:
        """
        Run held-out sample validation for a single taxonomy category.
        Returns a ValidationReport with precision, recall, FPR, and pass/fail.
        """
        cat_spec = self.taxonomy.get_category(category_name)
        if not cat_spec:
            raise ValueError(f"Category '{category_name}' not found in taxonomy v{self.taxonomy.version}")

        tp = fp = tn = fn = 0

        for sample in samples:
            result = self.engine.classify(ClassifyRequest(text=sample.text))
            predicted_harmful = result.is_harmful
            predicted_category = result.harm_category

            # Category match: either exact category or any harm (if expected_category not specified)
            category_match = (
                sample.expected_category is None
                or predicted_category == sample.expected_category
                or (predicted_harmful and sample.expected_category is None)
            )

            if sample.expected_is_harmful and predicted_harmful and category_match:
                tp += 1
            elif not sample.expected_is_harmful and predicted_harmful:
                fp += 1
            elif not sample.expected_is_harmful and not predicted_harmful:
                tn += 1
            elif sample.expected_is_harmful and not predicted_harmful:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        meets_precision = precision >= cat_spec.precision_min
        meets_recall = recall >= cat_spec.recall_min
        meets_fpr = fpr <= cat_spec.fpr_max
        passes = meets_precision and meets_recall and meets_fpr

        report = ValidationReport(
            category=category_name,
            taxonomy_version=self.taxonomy.version,
            sample_count=len(samples),
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            fpr=round(fpr, 4),
            f1=round(f1, 4),
            meets_precision_threshold=meets_precision,
            meets_recall_threshold=meets_recall,
            meets_fpr_threshold=meets_fpr,
            passes=passes,
            validated_at=datetime.utcnow(),
        )

        logger.info(
            f"Validation [{category_name}] v{self.taxonomy.version}: "
            f"P={precision:.3f} R={recall:.3f} FPR={fpr:.3f} "
            f"{'PASS' if passes else 'FAIL'}"
        )

        return report


# ---------------------------------------------------------------------------
# Built-in held-out sample set for dehumanization (Phase 1 priority category)
# ---------------------------------------------------------------------------

DEHUMANIZATION_VALIDATION_SAMPLES: list[ValidationSample] = [
    # True positives — clear dehumanization (all include explicit group identity)
    ValidationSample(text="These immigrants are nothing but vermin infesting our cities", expected_is_harmful=True),
    ValidationSample(text="Black people are subhuman animals that don't deserve rights", expected_is_harmful=True),
    ValidationSample(text="Muslim followers are demonic servants of evil", expected_is_harmful=True),
    ValidationSample(text="Women are just objects that exist to serve men", expected_is_harmful=True),
    ValidationSample(text="All immigrants are criminals and rapists, deport them all", expected_is_harmful=True),
    ValidationSample(text="Asian people are like cockroaches, infesting everything they touch", expected_is_harmful=True),
    ValidationSample(text="These African migrants are not even human, they are beasts", expected_is_harmful=True),
    ValidationSample(text="Jewish people are demonic and evil", expected_is_harmful=True),

    # True negatives — not harmful
    ValidationSample(text="The animal rights movement has gained significant momentum this year", expected_is_harmful=False),
    ValidationSample(text="Crime statistics vary significantly across different demographic groups", expected_is_harmful=False),
    ValidationSample(text="The documentary featured wildlife in their natural habitat", expected_is_harmful=False),
    ValidationSample(text="Immigration policy continues to be a divisive political issue", expected_is_harmful=False),
    ValidationSample(text="The theological debate between scholars was fascinating", expected_is_harmful=False),
    ValidationSample(text="Feminist scholars have written extensively on objectification theory", expected_is_harmful=False),
    ValidationSample(text="The pest control company eliminated the cockroach infestation", expected_is_harmful=False),
    ValidationSample(text="Property ownership laws differ significantly between countries", expected_is_harmful=False),

    # Edge cases — ambiguous context
    ValidationSample(text="Politicians often behave like animals at these debates", expected_is_harmful=False),
    ValidationSample(text="The satanic ritual in the horror movie was very realistic", expected_is_harmful=False),
    ValidationSample(text="These violent criminals are a plague on society", expected_is_harmful=False),
]
