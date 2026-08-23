from __future__ import annotations

from fastapi.testclient import TestClient

from oin.api.app import app


def test_lockdown_off_does_not_block_observers(monkeypatch):
    monkeypatch.delenv("OIN_PUBLIC_LOCKDOWN", raising=False)
    client = TestClient(app)
    response = client.post("/v1/observers", json={})
    assert response.status_code != 403


def test_lockdown_blocks_public_write_endpoints(monkeypatch):
    monkeypatch.setenv("OIN_PUBLIC_LOCKDOWN", "1")
    client = TestClient(app)
    for path in (
        "/v1/observations",
        "/v1/observers",
        "/v1/replication/pull",
        "/v1/replication/push",
    ):
        response = client.post(path, json={})
        assert response.status_code == 403
        assert response.json()["detail"] == "endpoint disabled on public test node"


def test_lockdown_allows_healthz(monkeypatch):
    monkeypatch.setenv("OIN_PUBLIC_LOCKDOWN", "1")
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_oversized_content_length_rejected():
    client = TestClient(app)
    response = client.post(
        "/v1/captures",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": str(11 * 1024 * 1024)},
    )
    assert response.status_code == 413
