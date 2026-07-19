"""
tests/api/test_api.py — Smoke tests for the FastAPI routes.

Exercises each endpoint once end-to-end against the real app (not mocked),
using a per-test-run tracking DB so tests don't pollute a shared dev.db.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", autouse=True)
def isolated_tracking_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("api_test_db") / "tracking.db"
    os.environ["TRACKING_DB_URL"] = f"sqlite:///{db_path}"
    yield
    os.environ.pop("TRACKING_DB_URL", None)


@pytest.fixture
def client(isolated_tracking_db):
    from narrative_harm_classifier.core.config import get_settings
    get_settings.cache_clear()
    from narrative_harm_classifier.api.main import create_app
    return TestClient(create_app())


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "taxonomy_version" in body


def test_classify_single(client):
    resp = client.post(
        "/classify/",
        json={"text": "Muslim followers are demonic servants of evil"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_harmful"] is True
    assert body["harm_category"] == "dehumanization"


def test_classify_batch(client):
    resp = client.post(
        "/classify/batch",
        json={"items": [{"text": "The weather is nice today"}, {"text": "Women are just property"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["harmful_count"] == 1


def test_validate_dehumanization(client):
    resp = client.post("/validate/dehumanization")
    assert resp.status_code == 200
    body = resp.json()
    assert body["passes"] is True


def test_benchmark_run(client):
    resp = client.post("/benchmark/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"]["precision"] == 1.0
    assert body["overall"]["recall"] == 1.0


def test_tracking_observe_and_profile(client):
    source_id = f"test-source-{uuid.uuid4().hex[:8]}"

    resp = client.post(f"/tracking/{source_id}/observe", json={"text": "All immigrants are criminals"})
    assert resp.status_code == 200

    resp = client.get(f"/tracking/{source_id}")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["source_id"] == source_id
    assert profile["observation_count"] == 1


def test_tracking_profile_404_when_unknown(client):
    resp = client.get(f"/tracking/never-observed-{uuid.uuid4().hex[:8]}")
    assert resp.status_code == 404


def test_tracking_list(client):
    source_id = f"test-list-{uuid.uuid4().hex[:8]}"
    client.post(f"/tracking/{source_id}/observe", json={"text": "Something harmless"})

    resp = client.get("/tracking")
    assert resp.status_code == 200
    profiles = resp.json()
    assert any(p["source_id"] == source_id for p in profiles)


def test_tracking_verify_intact(client):
    source_id = f"test-verify-{uuid.uuid4().hex[:8]}"
    client.post(f"/tracking/{source_id}/observe", json={"text": "Immigration policy is a complex issue"})

    resp = client.get(f"/tracking/{source_id}/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["intact"] is True
    assert body["observation_count"] == 1


def test_tracking_verify_404_when_unknown(client):
    resp = client.get(f"/tracking/never-observed-{uuid.uuid4().hex[:8]}/verify")
    assert resp.status_code == 404


def test_classify_multilingual(client):
    resp = client.post(
        "/classify/",
        json={"text": "Todos los inmigrantes son criminales, deportarlos a todos", "language": "es"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_harmful"] is True
    assert body["language"] == "es"
    assert body["language_confidence"] == "verified"
