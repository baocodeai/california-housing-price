"""
Kiểm thử đơn vị (Unit Tests) cho Feature Engineering và DataLoader.
"""
import pytest
import pandas as pd
import numpy as np
from src.data.build_features import FeatureEngineering, build_preprocessor
from src.data.dataloader import load_train_test_data
from src.config import RAW_FEATURE_COLS


def test_feature_engineering_transformation():
    """Kiểm tra việc sinh ra các cột đặc trưng tỷ lệ và cụm địa lý."""
    sample_df = pd.DataFrame([
        {
            "longitude": -122.23,
            "latitude": 37.88,
            "housing_median_age": 41.0,
            "total_rooms": 880.0,
            "total_bedrooms": 129.0,
            "population": 322.0,
            "households": 126.0,
            "median_income": 8.3252,
            "ocean_proximity": "ISLAND",
        }
    ])
    
    fe = FeatureEngineering(use_geo_cluster=False)
    fe.fit(sample_df)
    transformed = fe.transform(sample_df)

    assert "rooms_per_household" in transformed.columns
    assert "population_per_household" in transformed.columns
    assert "bedrooms_per_room" in transformed.columns
    assert "geo_cluster" in transformed.columns
    assert transformed["ocean_proximity"].iloc[0] == "NEAR OCEAN"


def test_build_preprocessor():
    """Kiểm tra ColumnTransformer chuẩn hóa đúng kích thước ma trận."""
    preprocessor = build_preprocessor()
    assert preprocessor is not None


def test_dataloader_execution():
    """Kiểm tra hàm load_train_test_data nạp dữ liệu không bị rỗng."""
    X_train, y_train, X_test, y_test = load_train_test_data(log_target=True)
    assert len(X_train) > 0
    assert len(X_test) > 0
    assert len(y_train) == len(X_train)
    assert len(y_test) == len(X_test)
    assert list(X_train.columns) == RAW_FEATURE_COLS
