import pytest
from fastapi.testclient import TestClient

from app.main import app, get_analyzer
from app.models import ClaudeAnalysis, Subscores
from app.services.analyzer import AnalyzerError


class FakeAnalyzer:
    model = "fake-model"

    def analyze(self, brief: str) -> ClaudeAnalysis:
        return ClaudeAnalysis(
            summary=f"Resume de: {brief[:20]}",
            subscores=Subscores(clarity=80, budget=40, urgency=60, offer_fit=20),
            questions=["q1", "q2", "q3"],
        )


class FailingAnalyzer:
    model = "fake-model"

    def analyze(self, brief: str) -> ClaudeAnalysis:
        raise AnalyzerError("boom")


client = TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_analyze_success():
    app.dependency_overrides[get_analyzer] = lambda: FakeAnalyzer()
    resp = client.post("/analyze", json={"brief": "Le client veut un portail RH"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 51
    assert body["model"] == "fake-model"
    assert len(body["questions"]) == 3
    assert body["subscores"]["clarity"] == 80


def test_analyze_empty_brief_rejected():
    app.dependency_overrides[get_analyzer] = lambda: FakeAnalyzer()
    resp = client.post("/analyze", json={"brief": ""})
    assert resp.status_code == 422


def test_analyze_upstream_failure():
    app.dependency_overrides[get_analyzer] = lambda: FailingAnalyzer()
    resp = client.post("/analyze", json={"brief": "un brief"})
    assert resp.status_code == 502


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()
