"""
Kiểm thử tích hợp (Integration Tests) cho toàn bộ hệ thống API FastAPI.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Kiểm tra endpoint gốc trả về status online."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_health_and_probes():
    """Kiểm tra health, live, và ready probes."""
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] in ["healthy", "degraded"]

    res_live = client.get("/api/v1/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    res_ready = client.get("/api/v1/ready")
    assert res_ready.status_code in [200, 503]


def test_predict_endpoint_valid():
    """Kiểm tra API dự đoán với dữ liệu hợp lệ."""
    payload = {
        "longitude": -122.23,
        "latitude": 37.88,
        "housing_median_age": 41.0,
        "total_rooms": 880.0,
        "total_bedrooms": 129.0,
        "population": 322.0,
        "households": 126.0,
        "median_income": 8.3252,
        "ocean_proximity": "NEAR BAY",
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["predicted_price"] > 0
    assert "formatted_price" in data


def test_predict_endpoint_invalid_bounds():
    """Kiểm tra chặn lỗi 422 khi tọa độ nằm ngoài phạm vi bang California."""
    payload = {
        "longitude": -100.0,  # Ngoài phạm vi California (-125 đến -114)
        "latitude": 37.88,
        "housing_median_age": 41.0,
        "total_rooms": 880.0,
        "total_bedrooms": 129.0,
        "population": 322.0,
        "households": 126.0,
        "median_income": 8.3252,
        "ocean_proximity": "NEAR BAY",
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422


def test_predict_batch():
    """Kiểm tra API dự đoán theo lô (Batch Prediction)."""
    payload = {
        "items": [
            {
                "longitude": -122.23,
                "latitude": 37.88,
                "housing_median_age": 41.0,
                "total_rooms": 880.0,
                "total_bedrooms": 129.0,
                "population": 322.0,
                "households": 126.0,
                "median_income": 8.3252,
                "ocean_proximity": "NEAR BAY",
            },
            {
                "longitude": -118.25,
                "latitude": 34.05,
                "housing_median_age": 25.0,
                "total_rooms": 2000.0,
                "total_bedrooms": 400.0,
                "population": 1500.0,
                "households": 380.0,
                "median_income": 4.5,
                "ocean_proximity": "<1H OCEAN",
            },
        ]
    }
    response = client.post("/api/v1/predict-batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_items"] == 2
    assert len(data["predictions"]) == 2


def test_prometheus_metrics():
    """Kiểm tra endpoint Prometheus metrics hoạt động."""
    response = client.get("/prometheus-metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_history_endpoint():
    """Kiểm tra endpoint lấy lịch sử dự đoán."""
    response = client.get("/api/v1/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data
    assert "history" in data


def test_metrics_endpoint():
    """Kiểm tra endpoint đối chuẩn các mô hình (benchmarks)."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_drift_status_endpoint():
    """Kiểm tra endpoint đo lường Data Drift."""
    response = client.get("/api/v1/drift-status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
