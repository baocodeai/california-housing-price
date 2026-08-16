import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Quản lý cấu hình toàn cục và các biến môi trường của hệ thống Backend.
    """
    PROJECT_NAME: str = "California Housing Price Prediction API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Môi trường thực thi
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")
    
    # Đường dẫn thư mục gốc và các artifacts
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    MODEL_PATH: Path = BASE_DIR / "models" / "stacking_pipeline.joblib"
    METADATA_PATH: Path = BASE_DIR / "models" / "model_metadata.json"
    
    # Đường dẫn dữ liệu (tự động nhận diện data/raw/housing.csv hoặc fallback data/housing.csv)
    RAW_DATA_PATH: Path = BASE_DIR / "data" / "raw" / "housing.csv"
    DATA_PATH: Path = (
        BASE_DIR / "data" / "raw" / "housing.csv"
        if (BASE_DIR / "data" / "raw" / "housing.csv").exists()
        else BASE_DIR / "data" / "housing.csv"
    )
    DB_PATH: Path = BASE_DIR / "backend" / "history.db"
    
    # Cấu hình danh sách tên miền CORS được phép truy cập
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]
    
    # Giới hạn tần suất request (Rate Limiting)
    RATE_LIMIT_PREDICT: str = "60/minute"
    RATE_LIMIT_BATCH: str = "20/minute"
    
    # Tùy chọn bật Prometheus
    ENABLE_PROMETHEUS: bool = True

    class Config:
        case_sensitive = True


settings = Settings()
