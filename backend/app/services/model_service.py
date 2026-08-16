"""
Dịch vụ quản lý vòng đời và thực thi suy luận (Inference Service) của mô hình Machine Learning.
Áp dụng mẫu thiết kế Singleton đảm bảo mô hình chỉ được nạp vào bộ nhớ RAM một lần duy nhất.
"""
import os
import json
import time
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.housing import HouseFeatures
from src.data.build_features import FeatureEngineering


class ModelService:
    """
    Singleton service quản lý vòng đời, làm nóng bộ đệm (pre-warm) và thực hiện
    suy luận dự đoán giá nhà California.
    """
    _instance: Optional["ModelService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self.version = "1.0.0"
        self.load_model()
        self._initialized = True

    def load_model(self) -> bool:
        """
        Nạp mô hình pipeline từ đĩa và đăng ký class FeatureEngineering
        vào __main__ cùng sys.modules để tương thích hoàn toàn với joblib / pickle.
        """
        import __main__
        import sys
        import src.data.build_features
        __main__.FeatureEngineering = FeatureEngineering
        sys.modules["src.features.pipeline"] = src.data.build_features

        model_path = settings.MODEL_PATH
        metadata_path = settings.METADATA_PATH

        if not model_path.exists():
            logger.warning(f"Không tìm thấy file mô hình tại: {model_path}")
            return False

        try:
            logger.info(f"Đang nạp mô hình artifact từ {model_path}...")
            self.model = joblib.load(str(model_path))
            
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                    self.version = self.metadata.get("model_version", "1.0.0")
            
            # Làm nóng mô hình bằng một dự đoán giả lập
            self._warm_up()
            logger.info(f"Đã nạp và làm nóng mô hình thành công (Phiên bản: {self.version})")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi nạp mô hình: {e}", exc_info=True)
            self.model = None
            return False

    def _warm_up(self):
        """
        Thực hiện một lượt suy luận giả lập để nạp sẵn bộ nhớ cache / JIT.
        """
        if self.model is None:
            return
        dummy_df = pd.DataFrame([{
            "longitude": -122.23,
            "latitude": 37.88,
            "housing_median_age": 41.0,
            "total_rooms": 880.0,
            "total_bedrooms": 129.0,
            "population": 322.0,
            "households": 126.0,
            "median_income": 8.3252,
            "ocean_proximity": "NEAR BAY",
        }])
        self.model.predict(dummy_df)

    def is_loaded(self) -> bool:
        """Kiểm tra mô hình đã được nạp thành công vào bộ nhớ hay chưa."""
        return self.model is not None

    def predict_single(self, features: HouseFeatures) -> Dict[str, Any]:
        """
        Thực hiện suy luận cho một căn nhà đơn lẻ và đo lường thời gian trễ (latency).
        """
        if self.model is None:
            raise RuntimeError("Mô hình chưa được nạp vào máy chủ.")

        df = pd.DataFrame([features.model_dump()])
        
        start_time = time.perf_counter()
        pred_log = self.model.predict(df)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Biến đổi ngược hàm log về giá trị USD thực tế: exp(log_price)
        predicted_price = float(np.exp(pred_log[0]))

        return {
            "predicted_price": round(predicted_price, 2),
            "formatted_price": f"${predicted_price:,.2f}",
            "model_version": self.version,
            "inference_latency_ms": round(latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def predict_batch(self, items: List[HouseFeatures]) -> Dict[str, Any]:
        """
        Thực hiện suy luận hàng loạt bằng cơ chế vector hóa để đạt thông lượng (throughput) tối đa.
        """
        if self.model is None:
            raise RuntimeError("Mô hình chưa được nạp vào máy chủ.")

        df = pd.DataFrame([item.model_dump() for item in items])
        
        start_time = time.perf_counter()
        pred_log = self.model.predict(df)
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        predicted_prices = np.exp(pred_log)
        
        results = [
            {
                "index": i,
                "predicted_price": round(float(price), 2),
                "formatted_price": f"${float(price):,.2f}",
            }
            for i, price in enumerate(predicted_prices)
        ]

        return {
            "status": "success",
            "total_items": len(items),
            "predictions": results,
            "total_inference_latency_ms": round(total_latency_ms, 2),
            "model_version": self.version,
        }

    def get_scatter_data(self, sample_size: int = 100) -> List[Dict[str, float]]:
        """
        Lấy mẫu ngẫu nhiên và sinh dữ liệu Actual vs Predicted phục vụ vẽ biểu đồ giao diện.
        """
        if self.model is None:
            raise RuntimeError("Mô hình chưa được nạp.")

        data_path = settings.DATA_PATH
        if not data_path.exists():
            raise FileNotFoundError("Không tìm thấy dữ liệu tham chiếu.")

        df = pd.read_csv(data_path)
        # Lọc các dòng bị trần
        df = df[(df["housing_median_age"] < 52) & (df["median_house_value"] < 500000)].dropna()
        df_sample = df.sample(n=min(sample_size, len(df)), random_state=42).copy()

        actuals = df_sample["median_house_value"].values
        features_df = df_sample[[
            "longitude", "latitude", "housing_median_age", "total_rooms",
            "total_bedrooms", "population", "households", "median_income", "ocean_proximity"
        ]]

        pred_log = self.model.predict(features_df)
        preds = np.exp(pred_log)

        return [
            {"actual": float(a), "predicted": round(float(p), 2)}
            for a, p in zip(actuals, preds)
        ]


model_service = ModelService()
