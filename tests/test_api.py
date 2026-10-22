import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from tests.conftest import feature_records


def _client(monkeypatch, tmp_path, model_dir):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("MODEL_PATH", str(model_dir / "fraud_model.joblib"))
    monkeypatch.setenv("MODEL_METADATA_PATH", str(model_dir / "model_metadata.json"))
    for name in [m for m in sys.modules if m.startswith("model_service")]:
        del sys.modules[name]
    main = importlib.import_module("model_service.main")
    return TestClient(main.app)


@pytest.fixture()
def client(monkeypatch, tmp_path, trained_model_dir):
    with _client(monkeypatch, tmp_path, trained_model_dir) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["model_loaded"] is True
    assert body["model_version"] == "test-model"


def test_batch_prediction_is_saved_with_features(client, prepared_df):
    records = feature_records(prepared_df.head(5))
    response = client.post("/predict", json={"transactions": records, "source": "scheduled"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    assert body["model_version"] == "test-model"

    past = client.get("/past-predictions", params={"source": "scheduled"}).json()
    assert past["count"] == 5
    assert past["predictions"][0]["features"]["time_period"] in {"night", "morning", "afternoon", "evening"}
    assert client.get("/past-predictions", params={"source": "webapp"}).json()["count"] == 0


def test_invalid_input_returns_422(client, prepared_df):
    record = feature_records(prepared_df.head(1))[0]
    record["time_period"] = "XYZ"
    assert client.post("/predict", json={"transactions": [record]}).status_code == 422
    assert client.post("/predict", json={"transactions": []}).status_code == 422


def test_bad_date_range_returns_400(client):
    response = client.get("/past-predictions", params={"start_date": "2026-02-01", "end_date": "2026-01-01"})
    assert response.status_code == 400


def test_unknown_prediction_returns_404(client):
    assert client.get("/past-predictions/123456").status_code == 404


def test_no_model_returns_503(monkeypatch, tmp_path, prepared_df):
    with _client(monkeypatch, tmp_path, tmp_path / "no_model_here") as c:
        assert c.get("/health").json()["model_loaded"] is False
        response = c.post("/predict", json={"transactions": feature_records(prepared_df.head(1))})
        assert response.status_code == 503
