import pytest
from fastapi.testclient import TestClient

from app.main import app, get_analyzer, get_store
from app.models import ClaudeAnalysis, Subscores
from app.services.store import InMemoryStore


class FakeAnalyzer:
    model = "fake-model"

    def analyze(self, brief: str) -> ClaudeAnalysis:
        return ClaudeAnalysis(
            summary=f"Resume de: {brief[:20]}",
            subscores=Subscores(clarity=80, budget=40, urgency=60, offer_fit=20),
            questions=["q1", "q2", "q3"],
        )


client = TestClient(app)


@pytest.fixture(autouse=True)
def _overrides():
    store = InMemoryStore()
    app.dependency_overrides[get_analyzer] = lambda: FakeAnalyzer()
    app.dependency_overrides[get_store] = lambda: store
    yield
    app.dependency_overrides.clear()


def test_analyze_persists_and_returns_id():
    resp = client.post("/analyze", json={"brief": "Portail RH"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"]
    assert body["created_at"]


def test_history_list_and_detail():
    r1 = client.post("/analyze", json={"brief": "Brief A"})
    client.post("/analyze", json={"brief": "Brief B"})
    qid = r1.json()["id"]

    listed = client.get("/qualifications")
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    detail = client.get(f"/qualifications/{qid}")
    assert detail.status_code == 200
    assert detail.json()["id"] == qid


def test_detail_not_found():
    resp = client.get("/qualifications/inconnu")
    assert resp.status_code == 404
