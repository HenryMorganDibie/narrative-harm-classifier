"""
tests/unit/test_cli.py — Smoke tests for the `nhc` CLI commands.

Uses Typer's CliRunner to invoke commands in-process (no subprocess), with
an isolated tracking DB so runs don't pollute a shared dev.db.
"""

import os
import uuid

import pytest
from typer.testing import CliRunner

from narrative_harm_classifier.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_tracking_db(tmp_path):
    db_path = tmp_path / "cli_test_tracking.db"
    os.environ["TRACKING_DB_URL"] = f"sqlite:///{db_path}"
    from narrative_harm_classifier.core.config import get_settings
    get_settings.cache_clear()
    yield
    os.environ.pop("TRACKING_DB_URL", None)
    get_settings.cache_clear()


def test_classify_command():
    result = runner.invoke(app, ["classify", "Muslim followers are demonic servants of evil"])
    assert result.exit_code == 0
    assert '"is_harmful": true' in result.stdout


def test_benchmark_run_command():
    result = runner.invoke(app, ["benchmark", "run"])
    assert result.exit_code == 0
    assert "overall" in result.stdout


def test_track_observe_show_list_commands():
    source_id = f"cli-test-{uuid.uuid4().hex[:8]}"

    result = runner.invoke(app, ["track", "observe", source_id, "All immigrants are criminals"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["track", "show", source_id])
    assert result.exit_code == 0
    assert source_id in result.stdout

    result = runner.invoke(app, ["track", "list"])
    assert result.exit_code == 0
    assert source_id in result.stdout


def test_track_show_unknown_source_exits_nonzero():
    result = runner.invoke(app, ["track", "show", f"never-seen-{uuid.uuid4().hex[:8]}"])
    assert result.exit_code == 1
