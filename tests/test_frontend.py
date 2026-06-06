from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_has_form_and_sections():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="brief"' in html
    assert 'id="analyze-btn"' in html
    assert 'id="history"' in html
    assert "/static/app.js" in html


def test_static_app_js_served():
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    assert "analyze" in resp.text
