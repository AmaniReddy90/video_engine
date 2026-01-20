from fastapi.testclient import TestClient

from vistar_engine.server import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_models_roundtrip():
    payload = {
        "mode": "procedural",
        "comfyui": {"url": "http://127.0.0.1:8188"},
        "sd": {},
        "animatediff": {},
        "tts": {},
        "music": {},
    }
    response = client.post("/models", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["registry"]["mode"] == "procedural"


def test_create_project():
    spec = {
        "version": "1.0",
        "title": "Test",
        "format": ["shorts"],
        "targets": {"shorts": {"duration_sec": 20, "aspect": "9:16", "resolution": "1080x1920"}},
        "scenes": [{"id": "S1", "summary": "Scene", "beats": ["A"], "dialogue": []}],
    }
    response = client.post("/projects", json=spec)
    assert response.status_code == 200
    assert "project_id" in response.json()
