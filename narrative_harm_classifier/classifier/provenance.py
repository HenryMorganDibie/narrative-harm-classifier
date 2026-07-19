"""
classifier/provenance.py — Deterministic content hashing and a tamper-evident
hash chain for escalation-tracking observations.

content_hash() is a pure function of (text, context, taxonomy_version): the
same input always produces the same hash regardless of when it's computed,
so it can be used to verify "this exact text was classified under this
exact taxonomy version" independent of any particular run.

record_hash() chains each Observation to the one before it (genesis
GENESIS_HASH for the first record in a source's history), the same idea as
a git commit chain or a minimal Merkle-style ledger: altering any historical
record changes its hash, which no longer matches what every later record's
hash was computed from — making tampering detectable, not prevented.
"""

import hashlib
from datetime import datetime
from typing import Optional

GENESIS_HASH = "0" * 64


def content_hash(text: str, context: Optional[str], taxonomy_version: str) -> str:
    payload = f"{text}\x1f{context or ''}\x1f{taxonomy_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_hash(
    prev_hash: str,
    source_id: str,
    text_excerpt: str,
    is_harmful: bool,
    harm_mechanism: Optional[str],
    confidence: float,
    observed_at: datetime,
    content_hash_value: str,
) -> str:
    payload = "\x1f".join(
        [
            prev_hash,
            source_id,
            text_excerpt,
            str(is_harmful),
            harm_mechanism or "",
            f"{confidence:.6f}",
            observed_at.isoformat(),
            content_hash_value,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
