"""
Module dự đoán độc lập (Standalone Inference) cho mô hình Stacking:
Hỗ trợ nhận linh hoạt mọi kiểu dữ liệu đầu vào (DataFrame, Dict, Danh sách Dict, file JSON, hoặc CSV).
"""
import argparse
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, List, Dict, Any

from src.config import MODEL_PATH, RAW_FEATURE_COLS
from src.data.build_features import FeatureEngineering

# Đăng ký FeatureEngineering vào không gian tên __main__ và sys.modules để tương thích unpickle
import __main__
import sys
import src.data.build_features
__main__.FeatureEngineering = FeatureEngineering
sys.modules["src.features.pipeline"] = src.data.build_features


class StackingPredictor:
    """
    Lớp xử lý dự đoán linh hoạt cho mô hình Stacking Regressor.
    """
    def __init__(self, model_path: Union[str, Path] = MODEL_PATH):
        self.model_path = Path(model_path)
        self.model = None
        self._load()

    def _load(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file mô hình tại: {self.model_path}")
        self.model = joblib.load(str(self.model_path))

    def predict(self, data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any], str, Path]) -> pd.DataFrame:
        """
        Thực hiện suy luận dự đoán trên các dạng dữ liệu đầu vào khác nhau.
        """
        if isinstance(data, (str, Path)):
            input_path = Path(data)
            if input_path.suffix == ".json":
                with open(input_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                df = pd.DataFrame(raw_data)
            else:
                df = pd.read_csv(input_path)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise TypeError(f"Kiểu dữ liệu không được hỗ trợ: {type(data)}")

        features_df = df[RAW_FEATURE_COLS]
        pred_log = self.model.predict(features_df)
        pred_prices = np.exp(pred_log)

        result_df = df.copy()
        result_df["predicted_price"] = np.round(pred_prices, 2)
        result_df["formatted_price"] = [f"${p:,.2f}" for p in result_df["predicted_price"]]
        return result_df


def predict_from_file(input_file: str, model_path: Path = MODEL_PATH) -> pd.DataFrame:
    """Hàm tiện ích dự đoán giá nhà từ file dữ liệu đầu vào."""
    predictor = StackingPredictor(model_path=model_path)
    result_df = predictor.predict(input_file)
    print(f"[Inference] Đã tạo thành công {len(result_df)} kết quả dự đoán:")
    print(result_df[["longitude", "latitude", "median_income", "predicted_price", "formatted_price"]])
    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy dự đoán giá nhà bằng mô hình Stacking đã huấn luyện")
    parser.add_argument("-i", "--input", type=str, default="data/external/sample_houses.json", help="Đường dẫn file đầu vào (JSON hoặc CSV)")
    parser.add_argument("-m", "--model", type=str, default=str(MODEL_PATH), help="Đường dẫn file artifact mô hình")
    args = parser.parse_args()

    predict_from_file(args.input, Path(args.model))
