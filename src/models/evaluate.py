"""
Module tính toán và in báo cáo các chỉ số đánh giá mô hình hồi quy.
"""
import numpy as np
from typing import Dict, Any
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_absolute_percentage_error


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Tính toán các độ đo hiệu năng hồi quy chính: RMSE, MAE, R², MAPE.
    """
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    mape = float(mean_absolute_percentage_error(y_true, y_pred))
    
    return {
        "rmse": round(rmse, 2),
        "mae": round(mae, 2),
        "r2": round(r2, 4),
        "mape": round(mape, 4),
    }


def print_evaluation_report(metrics: Dict[str, float], model_name: str = "Model") -> None:
    """
    In bảng báo cáo hiệu năng định dạng đẹp mắt ra màn hình terminal.
    """
    print(f"==========================================")
    print(f" Báo cáo hiệu năng: {model_name}")
    print(f"==========================================")
    print(f"  RMSE (Sai số bình phương trung bình) : ${metrics['rmse']:,.2f}")
    print(f"  MAE  (Sai số tuyệt đối trung bình)    : ${metrics['mae']:,.2f}")
    print(f"  R²   (Hệ số xác định)                 : {metrics['r2']:.4f}")
    print(f"  MAPE (Tỷ lệ sai số phần trăm)         : {metrics['mape'] * 100:.2f}%")
    print(f"==========================================")
