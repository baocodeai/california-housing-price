"""
Bộ phát hiện độ lệch phân phối dữ liệu (Statistical Data Drift Detector):
Sử dụng kiểm định thống kê Kolmogorov-Smirnov 2 mẫu (Two-Sample KS-Test) để so sánh
phân phối của tập dữ liệu cơ sở (reference baseline) với dữ liệu thực tế nhận được từ production.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from scipy.stats import ks_2samp


class DataDriftDetector:
    """
    Lớp thực hiện kiểm định thống kê phát hiện Data Drift trên từng đặc trưng số.
    """
    def __init__(self, reference_df: pd.DataFrame, alpha: float = 0.05):
        self.reference_df = reference_df.dropna()
        self.alpha = alpha  # Ngưỡng ý nghĩa thống kê (mặc định 5%)
        self.numeric_features = [
            "longitude",
            "latitude",
            "housing_median_age",
            "total_rooms",
            "total_bedrooms",
            "population",
            "households",
            "median_income",
        ]

    def test_drift(self, current_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Thực hiện KS-Test trên từng đặc trưng số giữa phân phối tham chiếu và phân phối hiện tại.
        """
        if len(current_df) < 5:
            return {
                "status": "insufficient_data",
                "sample_count": len(current_df),
                "message": "Cần ít nhất 5 bản ghi lịch sử để thực hiện kiểm định thống kê drift.",
            }

        results = []
        drift_count = 0

        for col in self.numeric_features:
            if col not in current_df.columns:
                continue

            ref_vals = self.reference_df[col].astype(float).values
            curr_vals = current_df[col].astype(float).values

            stat, p_val = ks_2samp(ref_vals, curr_vals)
            has_drift = bool(p_val < self.alpha)
            if has_drift:
                drift_count += 1

            results.append({
                "feature": col,
                "ref_mean": round(float(np.mean(ref_vals)), 4),
                "current_mean": round(float(np.mean(curr_vals)), 4),
                "ks_statistic": round(float(stat), 4),
                "p_value": round(float(p_val), 6),
                "drift_detected": has_drift,
            })

        return {
            "status": "success",
            "total_features_tested": len(results),
            "drifted_features_count": drift_count,
            "overall_drift_detected": drift_count > 0,
            "current_sample_size": len(current_df),
            "feature_metrics": results,
        }
