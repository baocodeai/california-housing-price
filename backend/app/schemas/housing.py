"""
Định nghĩa các Pydantic Schemas xác thực dữ liệu đầu vào và đầu ra cho API.
"""
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


OceanProximityType = Literal["<1H OCEAN", "INLAND", "NEAR OCEAN", "NEAR BAY", "ISLAND"]


class HouseFeatures(BaseModel):
    """
    Schema xác thực dữ liệu đầu vào cho một căn nhà với các điều kiện ràng buộc biên nghiêm ngặt.
    """
    longitude: float = Field(
        ..., ge=-125.0, le=-114.0, description="Kinh độ trong phạm vi bang California (-125.0 đến -114.0)"
    )
    latitude: float = Field(
        ..., ge=32.0, le=42.0, description="Vĩ độ trong phạm vi bang California (32.0 đến 42.0)"
    )
    housing_median_age: float = Field(
        ..., ge=1.0, le=100.0, description="Tuổi trung vị của nhà trong khu vực (1 đến 100 năm)"
    )
    total_rooms: float = Field(
        ..., ge=1.0, le=50000.0, description="Tổng số phòng trong khu vực"
    )
    total_bedrooms: float = Field(
        ..., ge=1.0, le=20000.0, description="Tổng số phòng ngủ trong khu vực"
    )
    population: float = Field(
        ..., ge=1.0, le=50000.0, description="Tổng dân số cư trú trong khu vực"
    )
    households: float = Field(
        ..., ge=1.0, le=20000.0, description="Tổng số hộ gia đình trong khu vực"
    )
    median_income: float = Field(
        ..., ge=0.0, le=25.0, description="Thu nhập trung vị tính theo chục nghìn USD (ví dụ 8.32 = $83,200)"
    )
    ocean_proximity: OceanProximityType = Field(
        ..., description="Vị trí tương quan với đại dương"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
        }


class SinglePredictionResponse(BaseModel):
    """Phản hồi kết quả dự đoán đơn lẻ."""
    status: str = "success"
    predicted_price: float
    formatted_price: str
    model_version: str
    inference_latency_ms: float
    timestamp: str


class BatchPredictionRequest(BaseModel):
    """Yêu cầu dự đoán hàng loạt (Batch Prediction)."""
    items: List[HouseFeatures] = Field(..., max_items=500, description="Danh sách các căn nhà cần dự đoán")


class BatchPredictionItemResult(BaseModel):
    """Kết quả dự đoán từng phần tử trong lô."""
    index: int
    predicted_price: float
    formatted_price: str


class BatchPredictionResponse(BaseModel):
    """Phản hồi kết quả dự đoán hàng loạt."""
    status: str = "success"
    total_items: int
    predictions: List[BatchPredictionItemResult]
    total_inference_latency_ms: float
    model_version: str


class HealthResponse(BaseModel):
    """Phản hồi kiểm tra sức khỏe hệ thống."""
    status: str
    version: str
    environment: str
    model_loaded: bool
    model_version: Optional[str] = None
    uptime_seconds: float
    database_connected: bool


class PredictionHistoryRecord(BaseModel):
    """Bản ghi lịch sử dự đoán từ cơ sở dữ liệu."""
    id: int
    longitude: float
    latitude: float
    housing_median_age: float
    total_rooms: float
    total_bedrooms: float
    population: float
    households: float
    median_income: float
    ocean_proximity: str
    predicted_price: float
    created_at: str


class HistoryResponse(BaseModel):
    """Phản hồi danh sách lịch sử dự đoán."""
    total_records: int
    history: List[PredictionHistoryRecord]


class ScatterDataPoint(BaseModel):
    """Tọa độ điểm vẽ biểu đồ Actual vs Predicted."""
    actual: float
    predicted: float
