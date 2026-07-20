# Escalation-Chain Tracking

Most moderation tooling scores a single piece of text in isolation. This tracks a **source** — an
account, an outlet, a document stream, any caller-supplied `source_id` — across a sequence of
observations, and computes:

- **current severity** — the harm level of the most recent observation
- **rolling average severity** over a configurable window (default: last 20 observations)
- **trend** — `escalating` / `stable` / `de-escalating`, from a first-half-vs-second-half average
  severity comparison over the window (simple, explainable arithmetic — not a black-box model)
- **risk level** — `low` / `watch` / `elevated` / `critical`, derived from current severity bumped
  up one level when the trend is escalating

## Why arithmetic instead of a model?

Because the whole point of this project is that a human reviewer, an auditor, or a journalist can
look at *why* a source was flagged and verify it themselves — "the last 10 posts averaged severity
2.3 and the second half of the window is worse than the first half" is checkable by hand. A learned
trend model might be more accurate but would trade away exactly the transparency this tool is trying
to offer.

## The severity ladder

`narrative_harm_classifier/classifier/tracking/models.py` defines:

```
none < narrative_distortion < demonization/objectification < animalization/criminalization <
direct_call_to_violence
```

This is a simplified, project-specific model inspired by general narrative-escalation research (see
[Why this exists](../index.md#why-this-exists)). It is **not** a validated academic scale; it exists
to give a consistent, explainable ordering for trend computation, not to represent a scientifically
calibrated risk score.

## Persistence

Uses SQLAlchemy against `DATABASE_URL`/`TRACKING_DB_URL` — SQLite by default (zero config), Postgres
or Azure SQL for real deployments, same code path.

## CLI

```bash
nhc track observe <source_id> "<text>"
nhc track show <source_id>
nhc track list
nhc track verify <source_id>
```

## API

| Endpoint | Purpose |
|---|---|
| `POST /tracking/{source_id}/observe` | Classify and append to a source's history |
| `GET /tracking/{source_id}` | A source's escalation profile |
| `GET /tracking` | All tracked sources, sorted by risk |
| `GET /tracking/{source_id}/verify` | Recompute the hash chain and confirm it's intact |
