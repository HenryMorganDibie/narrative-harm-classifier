# Provenance & Tamper-Evidence

Every `ClassificationResult` carries a `content_hash` — SHA-256 of `(text, context, taxonomy_version)`.
It's deterministic: the same input under the same taxonomy version always hashes the same, regardless
of when it's computed, so it can be used to verify "this exact text was classified under this exact
taxonomy version" independent of any particular run.

For escalation tracking, each `Observation` is chained to the one before it — `record_hash` is a hash
of the previous record's hash plus this record's fields, the same idea as a git commit chain or a
minimal Merkle-style ledger. Altering any historical record (directly in the database, bypassing the
API) changes its hash, which no longer matches what every later record's hash was computed from:

```bash
nhc track verify <source_id>
```

reports `Chain intact: YES` or, on a tampered history, `NO — TAMPERING DETECTED` plus the first broken
observation id (also `GET /tracking/{source_id}/verify`).

!!! warning
    This **detects** tampering; it does not **prevent** it — nothing stops someone with direct
    database access from recomputing the whole chain to hide their edit. For real accountability-workflow
    use, pair this with normal database access controls and backups, not as a substitute for them.
