from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_index_renders():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Quote Catcher" in resp.text
