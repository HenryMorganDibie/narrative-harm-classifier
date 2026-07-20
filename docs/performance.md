# Performance

Measured by running [`scripts/measure_performance.py`](https://github.com/HenryMorganDibie/narrative-harm-classifier/blob/main/scripts/measure_performance.py)
yourself — these are not estimates. The script times the classification engine directly (5,000 calls,
after a 200-call warmup), not the HTTP layer, since network/ASGI overhead depends on how you deploy
it, not on the engine:

| Metric | Measured |
|---|---|
| Average classification latency | 0.14 ms |
| p95 latency | 0.24 ms |
| p99 latency | 0.35 ms |
| Throughput (single core) | ~424,000 texts/min |
| Engine memory overhead (taxonomy + compiled regex patterns, on top of the interpreter) | ~0.6 MB |
| Total process RSS (interpreter + FastAPI/Pydantic/SQLAlchemy loaded) | ~35 MB |

Captured on a single core of an Intel Core i7-9700 (8 logical CPUs available, not parallelized),
Python 3.12.10, Windows 11 — a rule-based regex engine has no reason to be slower on comparable
hardware, and may be faster on a less loaded machine. Run the script yourself for numbers on your own
hardware; the point is that anyone can reproduce this, not that this exact figure is guaranteed.

Sub-millisecond latency and near-zero marginal memory are exactly what you'd expect from a regex
engine rather than a neural model — that's the other side of the trade-off described in
[Why this exists](index.md#why-this-exists): cheap and fast enough to run on every message at scale,
in exchange for the contextual-language gaps in [Limitations](limitations.md).
