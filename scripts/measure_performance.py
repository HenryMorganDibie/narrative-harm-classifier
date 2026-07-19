"""
scripts/measure_performance.py — Reproducible latency/memory/throughput measurement.

Prints real, measured numbers for the classification engine (not the API
layer — HTTP overhead is a separate, deployment-specific concern). Anyone
can run this themselves and get their own numbers for their own hardware;
the README numbers are captured from a run of this exact script, not
estimated or hardcoded.

Usage: python scripts/measure_performance.py
"""

import gc
import os
import statistics
import time

import psutil

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.validators.benchmark import generate_benchmark_cases

WARMUP_CALLS = 200
TIMED_CALLS = 5000


def main():
    process = psutil.Process(os.getpid())
    gc.collect()
    mem_before_mb = process.memory_info().rss / (1024 * 1024)

    settings = get_settings()
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    engine = ClassificationEngine(taxonomy=taxonomy, azure_client=AzureNLPClient())

    cases = generate_benchmark_cases(settings.benchmark_templates_path)
    texts = [c.text for c in cases]

    gc.collect()
    mem_after_load_mb = process.memory_info().rss / (1024 * 1024)

    # Warm up (import/JIT-adjacent effects, first-call regex compilation caching, etc.)
    for i in range(WARMUP_CALLS):
        engine.classify(ClassifyRequest(text=texts[i % len(texts)]))

    latencies_ms = []
    start_all = time.perf_counter()
    for i in range(TIMED_CALLS):
        text = texts[i % len(texts)]
        start = time.perf_counter()
        engine.classify(ClassifyRequest(text=text))
        latencies_ms.append((time.perf_counter() - start) * 1000)
    total_s = time.perf_counter() - start_all

    gc.collect()
    mem_after_run_mb = process.memory_info().rss / (1024 * 1024)

    latencies_ms.sort()
    avg_ms = statistics.mean(latencies_ms)
    p50_ms = latencies_ms[len(latencies_ms) // 2]
    p95_ms = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99_ms = latencies_ms[int(len(latencies_ms) * 0.99)]
    throughput_per_min = (TIMED_CALLS / total_s) * 60

    print(f"Calls timed:              {TIMED_CALLS}")
    print(f"Average latency:          {avg_ms:.3f} ms")
    print(f"p50 latency:              {p50_ms:.3f} ms")
    print(f"p95 latency:              {p95_ms:.3f} ms")
    print(f"p99 latency:              {p99_ms:.3f} ms")
    print(f"Throughput (single core): {throughput_per_min:,.0f} texts/min")
    print(f"Process RSS before load:  {mem_before_mb:.1f} MB")
    print(f"Process RSS after load:   {mem_after_load_mb:.1f} MB")
    print(f"Process RSS after run:    {mem_after_run_mb:.1f} MB")
    print(f"Engine memory overhead:   {mem_after_load_mb - mem_before_mb:.1f} MB (taxonomy + compiled patterns)")


if __name__ == "__main__":
    main()
