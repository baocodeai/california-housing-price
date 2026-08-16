"""
Kiểm thử tích hợp (Integration Tests) cho dịch vụ và API tra cứu làm giàu đặc trưng (Enrichment).
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.enrichment_service import enrichment_service

client = TestClient(app)


def test_enrichment_service_direct():
    """Kiểm tra gọi trực tiếp GeospatialEnrichmentService với tọa độ vịnh San Francisco."""
    lat, lng = 37.88, -122.23
    data = enrichment_service.lookup_nearest_block(lat, lng)

    assert "total_rooms" in data
    assert "median_income" in data
    assert "ocean_proximity" in data
    assert "lookup_distance_km" in data
    assert data["lookup_distance_km"] >= 0.0


def test_enrichment_api_endpoint_success():
    """Kiểm tra gọi endpoint GET /api/v1/enrichment/lookup với tọa độ hợp lệ."""
    response = client.get("/api/v1/enrichment/lookup?latitude=37.88&longitude=-122.23")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "features" in data
    assert data["features"]["ocean_proximity"] in ["NEAR BAY", "NEAR OCEAN", "<1H OCEAN", "INLAND", "ISLAND"]


def test_enrichment_api_endpoint_invalid_bounds():
    """Kiểm tra chặn lỗi 422 khi tọa độ tra cứu nằm ngoài bang California."""
    # Vĩ độ 55.0 (vượt ra ngoài phạm vi California [32.0, 42.0])
    response = client.get("/api/v1/enrichment/lookup?latitude=55.0&longitude=-122.23")
    assert response.status_code == 422
