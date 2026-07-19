"""
classifier/validators/benchmark.py — Templated functional-test benchmark.

Generates a much larger, systematic test suite than the hand-picked
DEHUMANIZATION_VALIDATION_SAMPLES set, modeled on the HateCheck methodology
(https://arxiv.org/abs/2012.15606): concrete test cases are generated from
templates tagged with a `test_type` (explicit positive, implicit positive,
negation, counter-speech, obfuscated spelling, benign hard negatives), so a
regression in one specific capability (e.g. negation handling) is visible
even when the aggregate precision/recall looks fine.

This benchmark is expected to expose real weaknesses in the current
regex-based engine (negation, counter-speech, spelling obfuscation aren't
handled) — that's the point: honest measurement rather than a vanity metric.
"""

import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine

logger = logging.getLogger(__name__)


class BenchmarkCase(BaseModel):
    case_id: str
    harm_mechanism: str
    category: str
    test_type: str
    text: str
    expected_is_harmful: bool
    group_used: Optional[str] = None


class TestTypeReport(BaseModel):
    test_type: str
    sample_count: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    fpr: float
    f1: float


class GroupConsistencyEntry(BaseModel):
    template_id: str
    test_type: str
    consistent: bool
    verdicts: dict[str, bool]  # group -> predicted is_harmful


class BenchmarkReport(BaseModel):
    taxonomy_version: str
    sample_count: int
    overall: TestTypeReport
    by_test_type: list[TestTypeReport]
    group_consistency: list[GroupConsistencyEntry]
    generated_at: datetime


@lru_cache(maxsize=4)
def load_benchmark_templates(path: str) -> dict:
    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(f"Benchmark templates not found: {path}")
    with open(template_path) as f:
        return yaml.safe_load(f)


def generate_benchmark_cases(templates_path: str) -> list[BenchmarkCase]:
    """Expand templates x groups, plus standalone cases, into concrete BenchmarkCases."""
    raw = load_benchmark_templates(templates_path)
    groups = raw.get("groups", [])
    cases: list[BenchmarkCase] = []

    for template in raw.get("templates", []):
        for group_entry in groups:
            group = group_entry["group"]
            text = template["pattern"].format(group=group)
            cases.append(
                BenchmarkCase(
                    case_id=f"{template['template_id']}::{group}",
                    harm_mechanism=template["harm_mechanism"],
                    category=template["category"],
                    test_type=template["test_type"],
                    text=text,
                    expected_is_harmful=template["expected_is_harmful"],
                    group_used=group,
                )
            )

    for case in raw.get("standalone_cases", []):
        cases.append(
            BenchmarkCase(
                case_id=case["case_id"],
                harm_mechanism=case["harm_mechanism"],
                category=case["category"],
                test_type=case["test_type"],
                text=case["text"],
                expected_is_harmful=case["expected_is_harmful"],
                group_used=None,
            )
        )

    return cases


def _score(tp: int, fp: int, tn: int, fn: int) -> tuple[float, float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return round(precision, 4), round(recall, 4), round(fpr, 4), round(f1, 4)


class BenchmarkRunner:
    def __init__(self, engine: ClassificationEngine, taxonomy_version: str, templates_path: str):
        self.engine = engine
        self.taxonomy_version = taxonomy_version
        self.templates_path = templates_path

    def run(self) -> BenchmarkReport:
        cases = generate_benchmark_cases(self.templates_path)

        # predictions[case_id] = (expected, predicted)
        predictions: dict[str, tuple[bool, bool]] = {}
        # template_id -> {group: predicted}
        template_group_verdicts: dict[str, dict[str, bool]] = {}
        template_test_types: dict[str, str] = {}

        for case in cases:
            result = self.engine.classify(ClassifyRequest(text=case.text))
            predictions[case.case_id] = (case.expected_is_harmful, result.is_harmful)

            if case.group_used is not None:
                template_id = case.case_id.split("::", 1)[0]
                template_group_verdicts.setdefault(template_id, {})[case.group_used] = result.is_harmful
                template_test_types[template_id] = case.test_type

        by_test_type_map: dict[str, list[BenchmarkCase]] = {}
        for case in cases:
            by_test_type_map.setdefault(case.test_type, []).append(case)

        def confusion(case_list: list[BenchmarkCase]) -> tuple[int, int, int, int]:
            tp = fp = tn = fn = 0
            for c in case_list:
                expected, predicted = predictions[c.case_id]
                if expected and predicted:
                    tp += 1
                elif not expected and predicted:
                    fp += 1
                elif not expected and not predicted:
                    tn += 1
                else:
                    fn += 1
            return tp, fp, tn, fn

        overall_tp, overall_fp, overall_tn, overall_fn = confusion(cases)
        overall_p, overall_r, overall_fpr, overall_f1 = _score(overall_tp, overall_fp, overall_tn, overall_fn)
        overall = TestTypeReport(
            test_type="overall",
            sample_count=len(cases),
            true_positives=overall_tp,
            false_positives=overall_fp,
            true_negatives=overall_tn,
            false_negatives=overall_fn,
            precision=overall_p,
            recall=overall_r,
            fpr=overall_fpr,
            f1=overall_f1,
        )

        by_test_type = []
        for test_type, case_list in sorted(by_test_type_map.items()):
            tp, fp, tn, fn = confusion(case_list)
            p, r, fpr, f1 = _score(tp, fp, tn, fn)
            by_test_type.append(
                TestTypeReport(
                    test_type=test_type,
                    sample_count=len(case_list),
                    true_positives=tp,
                    false_positives=fp,
                    true_negatives=tn,
                    false_negatives=fn,
                    precision=p,
                    recall=r,
                    fpr=fpr,
                    f1=f1,
                )
            )

        group_consistency = []
        for template_id, verdicts in sorted(template_group_verdicts.items()):
            consistent = len(set(verdicts.values())) == 1
            group_consistency.append(
                GroupConsistencyEntry(
                    template_id=template_id,
                    test_type=template_test_types[template_id],
                    consistent=consistent,
                    verdicts=verdicts,
                )
            )

        logger.info(
            f"Benchmark v{self.taxonomy_version}: {len(cases)} cases, "
            f"overall P={overall_p:.3f} R={overall_r:.3f} FPR={overall_fpr:.3f}"
        )

        return BenchmarkReport(
            taxonomy_version=self.taxonomy_version,
            sample_count=len(cases),
            overall=overall,
            by_test_type=by_test_type,
            group_consistency=group_consistency,
            generated_at=datetime.utcnow(),
        )
