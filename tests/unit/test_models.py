"""
Kiểm thử đơn vị (Unit Tests) cho Model Service và các hàm đánh giá mô hình.
"""
import pytest
import numpy as np
from backend.app.services.model_service import ModelService
from backend.app.schemas.housing import HouseFeatures
from src.models.evaluate import calculate_metrics


def test_model_loading_and_single_prediction():
    """Kiểm tra nạp mô hình và suy luận đơn lẻ thành công."""
    service = ModelService()
    assert service.is_loaded() is True
    
    sample_input = HouseFeatures(
        longitude=-122.23,
        latitude=37.88,
        housing_median_age=41.0,
        total_rooms=880.0,
        total_bedrooms=129.0,
        population=322.0,
        households=126.0,
        median_income=8.3252,
        ocean_proximity="NEAR BAY",
    )
    
    result = service.predict_single(sample_input)
    assert result["predicted_price"] > 10000
    assert result["predicted_price"] < 1000000
    assert "inference_latency_ms" in result
    assert result["inference_latency_ms"] < 1500


def test_batch_prediction():
    """Kiểm tra dự đoán hàng loạt với nhiều căn nhà cùng lúc."""
    service = ModelService()
    items = [
        HouseFeatures(
            longitude=-122.23,
            latitude=37.88,
            housing_median_age=41.0,
            total_rooms=880.0,
            total_bedrooms=129.0,
            population=322.0,
            households=126.0,
            median_income=8.3252,
            ocean_proximity="NEAR BAY",
        ),
        HouseFeatures(
            longitude=-118.25,
            latitude=34.05,
            housing_median_age=25.0,
            total_rooms=2000.0,
            total_bedrooms=400.0,
            population=1500.0,
            households=380.0,
            median_income=4.5,
            ocean_proximity="<1H OCEAN",
        ),
    ]
    
    batch_result = service.predict_batch(items)
    assert batch_result["total_items"] == 2
    assert len(batch_result["predictions"]) == 2
    assert batch_result["predictions"][0]["predicted_price"] > 0


def test_calculate_metrics():
    """Kiểm tra tính đúng đắn của các công thức đo lường sai số RMSE, MAE, R², MAPE."""
    y_true = np.array([200000.0, 300000.0, 400000.0])
    y_pred = np.array([210000.0, 290000.0, 410000.0])
    metrics = calculate_metrics(y_true, y_pred)
    assert "rmse" in metrics
    assert "mae" in metrics
    assert "r2" in metrics
    assert "mape" in metrics
    assert metrics["r2"] > 0.9
