"""
api/routes/benchmark.py — Templated benchmark endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException

from narrative_harm_classifier.core.config import get_settings, Settings
from narrative_harm_classifier.classifier.factory import build_benchmark_runner
from narrative_harm_classifier.classifier.validators.benchmark import BenchmarkRunner, BenchmarkReport

router = APIRouter()


def get_runner(settings: Settings = Depends(get_settings)) -> BenchmarkRunner:
    return build_benchmark_runner(settings)


@router.post(
    "/run",
    response_model=BenchmarkReport,
    summary="Run the templated functional-test benchmark suite",
    description=(
        "Generates and runs a HateCheck-style templated test suite (explicit/implicit "
        "positives, negation, counter-speech, obfuscated spelling, cross-group consistency, "
        "and benign hard negatives). Returns aggregate and per-test-type precision/recall/FPR."
    ),
)
def run_benchmark(runner: BenchmarkRunner = Depends(get_runner)) -> BenchmarkReport:
    try:
        return runner.run()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
