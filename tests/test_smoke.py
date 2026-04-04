from fastapi.testclient import TestClient

from youtube_suite.api.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "creator" in r.json().get("service", "").lower()
