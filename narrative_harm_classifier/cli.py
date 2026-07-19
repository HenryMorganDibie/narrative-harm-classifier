"""
narrative_harm_classifier/cli.py — `nhc` command-line interface.

Ties together classification, the API server, escalation-chain tracking,
and the templated benchmark suite for local/scriptable use without needing
to write any Python or run curl against the API.
"""

import json
import sys
from typing import Optional

import typer

# Rationale/report text uses non-ASCII characters (e.g. "≥"). On Windows,
# stdout defaults to the legacy console codepage (cp1252) rather than UTF-8,
# which crashes on encode. Force UTF-8 so `nhc` works in a default terminal.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.taxonomy.loader import load_taxonomy
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient
from narrative_harm_classifier.classifier.tracking.store import get_store
from narrative_harm_classifier.classifier.tracking.tracker import EscalationTracker
from narrative_harm_classifier.classifier.validators.benchmark import BenchmarkRunner

app = typer.Typer(name="nhc", help="Narrative Harm Classifier — classify, track, and benchmark.")
track_app = typer.Typer(help="Escalation-chain tracking across a source's observation history.")
benchmark_app = typer.Typer(help="Templated functional-test benchmark suite.")
app.add_typer(track_app, name="track")
app.add_typer(benchmark_app, name="benchmark")


def _build_engine() -> tuple[ClassificationEngine, str]:
    settings = get_settings()
    taxonomy = load_taxonomy(settings.taxonomy_config_path)
    azure_client = AzureNLPClient(
        endpoint=settings.azure_text_analytics_endpoint,
        key=settings.azure_text_analytics_key,
    )
    return ClassificationEngine(taxonomy=taxonomy, azure_client=azure_client), taxonomy.version


def _build_tracker() -> EscalationTracker:
    settings = get_settings()
    engine, _ = _build_engine()
    store = get_store(settings.effective_tracking_db_url)
    return EscalationTracker(engine=engine, store=store)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Auto-reload on code changes (development only)"),
):
    """Start the FastAPI server (docs at http://<host>:<port>/docs)."""
    import uvicorn

    uvicorn.run("narrative_harm_classifier.api.main:app", host=host, port=port, reload=reload)


@app.command()
def classify(
    text: str = typer.Argument(..., help="Text to classify"),
    context: Optional[str] = typer.Option(None, help="Optional surrounding context"),
):
    """Classify a single text item and print the full result as JSON."""
    engine, _ = _build_engine()
    result = engine.classify(ClassifyRequest(text=text, context=context))
    typer.echo(result.model_dump_json(indent=2))


@track_app.command("observe")
def track_observe(
    source_id: str = typer.Argument(..., help="Identifier for the tracked source (URL, handle, doc id...)"),
    text: str = typer.Argument(..., help="Text to classify and append to this source's history"),
):
    """Classify a text and append it to a source's escalation history."""
    tracker = _build_tracker()
    obs = tracker.observe(source_id, ClassifyRequest(text=text))
    typer.echo(obs.model_dump_json(indent=2))


@track_app.command("show")
def track_show(
    source_id: str = typer.Argument(..., help="Source to show"),
    window: int = typer.Option(20, help="Number of most recent observations to consider"),
):
    """Show a source's current severity, trend, and risk level."""
    tracker = _build_tracker()
    profile = tracker.profile(source_id, window=window)
    if profile.observation_count == 0:
        typer.echo(f"No observations recorded for source '{source_id}'", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Source:              {profile.source_id}")
    typer.echo(f"Observations:        {profile.observation_count}")
    typer.echo(f"Current severity:    {profile.current_severity.name} ({int(profile.current_severity)})")
    typer.echo(f"Rolling avg severity:{profile.rolling_avg_severity:.2f}")
    typer.echo(f"Trend:               {profile.trend}")
    typer.echo(f"Risk level:          {profile.risk_level.upper()}")


@track_app.command("list")
def track_list(window: int = typer.Option(20, help="Number of most recent observations to consider per source")):
    """List all tracked sources, sorted by risk (highest first)."""
    tracker = _build_tracker()
    profiles = tracker.list_profiles(window=window)
    if not profiles:
        typer.echo("No tracked sources yet.")
        return

    typer.echo(f"{'SOURCE':<30}{'RISK':<10}{'TREND':<20}{'SEVERITY':<24}{'OBS':<5}")
    for p in profiles:
        typer.echo(
            f"{p.source_id:<30}{p.risk_level.upper():<10}{p.trend:<20}"
            f"{p.current_severity.name:<24}{p.observation_count:<5}"
        )


@benchmark_app.command("run")
def benchmark_run():
    """Run the templated benchmark suite and print aggregate + per-test-type results."""
    settings = get_settings()
    engine, taxonomy_version = _build_engine()
    runner = BenchmarkRunner(
        engine=engine,
        taxonomy_version=taxonomy_version,
        templates_path=settings.benchmark_templates_path,
    )
    report = runner.run()

    typer.echo(f"Taxonomy version: {report.taxonomy_version}")
    typer.echo(f"Total cases:      {report.sample_count}\n")

    typer.echo(f"{'TEST TYPE':<22}{'N':<6}{'PRECISION':<11}{'RECALL':<9}{'FPR':<8}{'F1':<8}")
    typer.echo(
        f"{'overall':<22}{report.overall.sample_count:<6}{report.overall.precision:<11}"
        f"{report.overall.recall:<9}{report.overall.fpr:<8}{report.overall.f1:<8}"
    )
    for t in report.by_test_type:
        typer.echo(f"{t.test_type:<22}{t.sample_count:<6}{t.precision:<11}{t.recall:<9}{t.fpr:<8}{t.f1:<8}")

    inconsistent = [g for g in report.group_consistency if not g.consistent]
    typer.echo(f"\nCross-group consistency: {len(report.group_consistency) - len(inconsistent)}/"
               f"{len(report.group_consistency)} templates consistent across groups")
    if inconsistent:
        typer.echo("Inconsistent templates (engine's verdict changed depending on which group was named):")
        for g in inconsistent:
            typer.echo(f"  {g.template_id} ({g.test_type}): {json.dumps(g.verdicts)}")


def main():
    app()


if __name__ == "__main__":
    main()
