from __future__ import annotations

from fastapi.testclient import TestClient

from model_service.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "model_loaded" in data
        assert "model_version" in data


def test_batch_prediction_and_storage():
    with TestClient(app) as client:
        tx1 = {"Time": 10.0, "Amount": 100.0}
        tx2 = {"Time": 20.0, "Amount": 200.0}
        for i in range(1, 29):
            tx1[f"V{i}"] = 0.05
            tx2[f"V{i}"] = -0.05

        payload = {
            "transactions": [tx1, tx2],
            "source": "ci_test_batch",
        }

        resp = client.post("/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_predictions"] == 2
        assert len(data["predictions"]) == 2

        pred0 = data["predictions"][0]
        assert pred0["predicted_class"] in [0, 1]
        assert 0.0 <= pred0["probability"] <= 1.0
        assert pred0["source"] == "ci_test_batch"
        assert pred0["model_version"] == "1.0.0"
        assert pred0["features"] is not None
        assert pred0["features"]["Amount"] == 100.0


def test_single_prediction_endpoint():
    with TestClient(app) as client:
        tx = {"Time": 50.0, "Amount": 30.0}
        for i in range(1, 29):
            tx[f"V{i}"] = 0.0

        payload = {
            "transaction": tx,
            "source": "ci_test_single",
        }

        resp = client.post("/predict/single", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["predicted_class"] in [0, 1]
        assert 0.0 <= data["probability"] <= 1.0
        assert data["source"] == "ci_test_single"


def test_get_predictions_with_filter():
    with TestClient(app) as client:
        # Fetch predictions filtered by source
        resp = client.get("/predictions?source=ci_test_batch")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert item["source"] == "ci_test_batch"
