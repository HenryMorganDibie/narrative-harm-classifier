"""
classifier/validators/i18n_smoke.py — Per-language smoke test runner.

Deliberately smaller in scope than the English benchmark (see
data/i18n_smoke_tests.yaml for why) — this confirms basic detection works
per language, broken out so a regression in one specific language is
visible rather than hidden in an aggregate.
"""

from pydantic import BaseModel

from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.core.yaml_loader import load_yaml_file
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine


class I18nSmokeCaseResult(BaseModel):
    language: str
    text: str
    expected_is_harmful: bool
    actual_is_harmful: bool

    @property
    def passed(self) -> bool:
        return self.expected_is_harmful == self.actual_is_harmful


class I18nSmokeReport(BaseModel):
    total: int
    passed: int
    failed_cases: list[I18nSmokeCaseResult]
    by_language: dict[str, tuple[int, int]]  # language -> (passed, total)


def run_i18n_smoke(engine: ClassificationEngine, path: str) -> I18nSmokeReport:
    raw = load_yaml_file(path)
    results: list[I18nSmokeCaseResult] = []

    for case in raw.get("cases", []):
        result = engine.classify(ClassifyRequest(text=case["text"], language=case["language"]))
        results.append(
            I18nSmokeCaseResult(
                language=case["language"],
                text=case["text"],
                expected_is_harmful=case["expected_is_harmful"],
                actual_is_harmful=result.is_harmful,
            )
        )

    by_language: dict[str, list[int]] = {}
    for r in results:
        counts = by_language.setdefault(r.language, [0, 0])
        counts[1] += 1
        if r.passed:
            counts[0] += 1

    return I18nSmokeReport(
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        failed_cases=[r for r in results if not r.passed],
        by_language={lang: (counts[0], counts[1]) for lang, counts in by_language.items()},
    )
