# Configuration

Copy `.env.example` to `.env`. Key settings:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` | General DB URL (Postgres/Azure SQL in prod) |
| `TRACKING_DB_URL` | falls back to `DATABASE_URL` | Escalation-tracking store |
| `AZURE_TEXT_ANALYTICS_ENDPOINT` / `_KEY` | unset | Optional NLP amplification |
| `TAXONOMY_CONFIG_PATH` | packaged `taxonomy_v1.yaml` | Override with a custom taxonomy |
| `BENCHMARK_TEMPLATES_PATH` | packaged `benchmark_templates.yaml` | Override with custom benchmark cases |
| `PATTERNS_DIR` | packaged `data/patterns/` | Override with your own per-language vocabulary files |
| `DOGWHISTLES_PATH` | packaged `dogwhistles.yaml` | Override with a custom coded-language lexicon |
| `I18N_SMOKE_TESTS_PATH` | packaged `i18n_smoke_tests.yaml` | Override with your own per-language smoke tests |

!!! note "Serverless / ephemeral filesystems"
    If you deploy the API on a platform with a read-only or ephemeral filesystem (e.g. Vercel
    serverless functions), point `DATABASE_URL`/`TRACKING_DB_URL` at a real hosted Postgres instance —
    SQLite needs a writable, persistent file, which those platforms don't provide between invocations.
    `/classify`, `/validate`, and `/benchmark/run` are all stateless and work fine regardless; only the
    `/tracking/*` endpoints touch the database.
