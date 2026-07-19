"""
classifier/tracking/store.py — Persistence for escalation-chain observations.

Uses SQLAlchemy Core (not the ORM) against Settings.effective_tracking_db_url,
which defaults to a local SQLite file (zero-config) and works unchanged
against Postgres for real deployments.
"""

from datetime import datetime
from functools import lru_cache
from typing import Optional

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    select,
    insert,
)

from narrative_harm_classifier.classifier.tracking.models import Observation, SeverityLevel

metadata = MetaData()

observations_table = Table(
    "observations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_id", String, nullable=False, index=True),
    Column("text_excerpt", String, nullable=False),
    Column("is_harmful", Boolean, nullable=False),
    Column("harm_category", String, nullable=False),
    Column("harm_mechanism", String, nullable=True),
    Column("confidence", Float, nullable=False),
    Column("severity", Integer, nullable=False),
    Column("observed_at", DateTime, nullable=False),
    Column("content_hash", String, nullable=False, server_default=""),
    Column("prev_hash", String, nullable=False, server_default=""),
    Column("record_hash", String, nullable=False, server_default=""),
)


class TrackingStore:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, future=True)
        metadata.create_all(self.engine)

    def add_observation(self, obs: Observation) -> Observation:
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(observations_table).values(
                    source_id=obs.source_id,
                    text_excerpt=obs.text_excerpt,
                    is_harmful=obs.is_harmful,
                    harm_category=obs.harm_category,
                    harm_mechanism=obs.harm_mechanism,
                    confidence=obs.confidence,
                    severity=int(obs.severity),
                    observed_at=obs.observed_at,
                    content_hash=obs.content_hash,
                    prev_hash=obs.prev_hash,
                    record_hash=obs.record_hash,
                )
            )
            obs.id = result.inserted_primary_key[0]
        return obs

    def last_record_hash(self, source_id: str) -> str:
        """Most recent record_hash for a source, or GENESIS_HASH if it has no history yet."""
        from narrative_harm_classifier.classifier.provenance import GENESIS_HASH

        with self.engine.connect() as conn:
            query = (
                select(observations_table.c.record_hash)
                .where(observations_table.c.source_id == source_id)
                .order_by(observations_table.c.observed_at.desc(), observations_table.c.id.desc())
                .limit(1)
            )
            row = conn.execute(query).first()
        return row[0] if row else GENESIS_HASH

    def history(self, source_id: str, limit: Optional[int] = None) -> list[Observation]:
        with self.engine.connect() as conn:
            query = (
                select(observations_table)
                .where(observations_table.c.source_id == source_id)
                .order_by(observations_table.c.observed_at.asc())
            )
            rows = conn.execute(query).mappings().all()

        history = [
            Observation(
                id=row["id"],
                source_id=row["source_id"],
                text_excerpt=row["text_excerpt"],
                is_harmful=row["is_harmful"],
                harm_category=row["harm_category"],
                harm_mechanism=row["harm_mechanism"],
                confidence=row["confidence"],
                severity=SeverityLevel(row["severity"]),
                observed_at=row["observed_at"],
                content_hash=row["content_hash"] or "",
                prev_hash=row["prev_hash"] or "",
                record_hash=row["record_hash"] or "",
            )
            for row in rows
        ]
        if limit is not None:
            history = history[-limit:]
        return history

    def list_source_ids(self) -> list[str]:
        with self.engine.connect() as conn:
            rows = conn.execute(select(observations_table.c.source_id).distinct()).all()
        return [r[0] for r in rows]


@lru_cache(maxsize=4)
def get_store(db_url: str) -> TrackingStore:
    return TrackingStore(db_url)
