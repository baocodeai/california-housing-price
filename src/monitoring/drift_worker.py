"""
Worker chạy ngầm giám sát Data Drift tự động:
Thực hiện định kỳ phân tích KS-Test và chỉ số ổn định dân số PSI (Population Stability Index)
giữa tập dữ liệu cơ sở và các lượt dự đoán được ghi nhận trong cơ sở dữ liệu.
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp

# Thêm project root vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_PATH, RAW_FEATURE_COLS
from backend.app.core.config import settings
from backend.app.db.session import get_db_connection
from backend.app.core.logging import logger


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
    """
    Tính toán chỉ số ổn định dân số (Population Stability Index - PSI).
    - PSI < 0.1: Phân phối ổn định, không có thay đổi đáng kể.
    - 0.1 <= PSI < 0.2: Có sự dịch chuyển nhẹ.
    - PSI >= 0.2: Trôi dạt dữ liệu nghiêm trọng (Cần huấn luyện lại mô hình).
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    percentiles = np.linspace(0, 100, num_buckets + 1)
    bucket_bounds = np.percentile(expected, percentiles)
    bucket_bounds[0] = -np.inf
    bucket_bounds[-1] = np.inf

    expected_counts, _ = np.histogram(expected, bins=bucket_bounds)
    actual_counts, _ = np.histogram(actual, bins=bucket_bounds)

    expected_pct = (expected_counts + 1e-5) / len(expected)
    actual_pct = (actual_counts + 1e-5) / len(actual)

    psi_val = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi_val)


def run_drift_check(min_samples: int = 10, export_report: bool = True) -> dict:
    """
    Thực hiện kiểm tra Data Drift bằng KS-Test và PSI trên tất cả các đặc trưng số.
    """
    logger.info("Bắt đầu kiểm tra Data Drift tự động...")
    
    if not DATA_PATH.exists():
        logger.error(f"Không tìm thấy tập dữ liệu cơ sở tại: {DATA_PATH}")
        return {"status": "error", "message": "Không tìm thấy dữ liệu cơ sở"}

    ref_df = pd.read_csv(DATA_PATH).dropna()
    conn = get_db_connection()
    try:
        curr_df = pd.read_sql_query("SELECT * FROM predictions", conn)
    finally:
        conn.close()

    sample_size = len(curr_df)
    if sample_size < min_samples:
        msg = f"Chưa đủ dữ liệu thực tế ({sample_size}/{min_samples}). Bỏ qua kiểm tra drift."
        logger.info(msg)
        return {"status": "insufficient_data", "sample_size": sample_size, "message": msg}

    numeric_features = [
        "longitude", "latitude", "housing_median_age", "total_rooms",
        "total_bedrooms", "population", "households", "median_income"
    ]

    feature_reports = []
    drifted_count = 0

    for feat in numeric_features:
        ref_vals = ref_df[feat].astype(float).values
        curr_vals = curr_df[feat].astype(float).values

        stat, p_val = ks_2samp(ref_vals, curr_vals)
        psi = calculate_psi(ref_vals, curr_vals)
        is_drift = bool(p_val < 0.05 or psi >= 0.2)

        if is_drift:
            drifted_count += 1

        feature_reports.append({
            "feature": feat,
            "ref_mean": round(float(np.mean(ref_vals)), 4),
            "current_mean": round(float(np.mean(curr_vals)), 4),
            "ks_statistic": round(float(stat), 4),
            "p_value": round(float(p_val), 6),
            "psi_score": round(float(psi), 4),
            "drift_detected": is_drift,
        })

    overall_drift = drifted_count > 0
    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.isoformat()

    report = {
        "timestamp": timestamp,
        "status": "drift_detected" if overall_drift else "normal",
        "overall_drift_detected": overall_drift,
        "drifted_features_count": drifted_count,
        "total_features_evaluated": len(numeric_features),
        "production_sample_size": sample_size,
        "features": feature_reports,
    }

    if export_report:
        reports_dir = PROJECT_ROOT / "data" / "drift_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"drift_report_{now_utc.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Đã xuất báo cáo drift ra {report_file}")

    if overall_drift:
        logger.warning(
            f"[CẢNH BÁO] Phát hiện Data Drift trên {drifted_count} đặc trưng! Khuyến nghị kiểm tra dữ liệu hoặc train lại mô hình."
        )
    else:
        logger.info(f"[BÌNH THƯỜNG] Kiểm tra Data Drift hoàn tất: Tất cả {len(numeric_features)} đặc trưng nằm trong giới hạn cho phép.")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dịch vụ tự động giám sát và phát hiện Data Drift")
    parser.add_argument("--min-samples", type=int, default=5, help="Số lượng bản ghi tối thiểu để chạy")
    parser.add_argument("--interval", type=int, default=0, help="Chu kỳ lặp lại theo giây (0 = chạy 1 lần duy nhất)")
    args = parser.parse_args()

    if args.interval > 0:
        logger.info(f"Khởi chạy worker Data Drift ở chế độ Daemon (Chu kỳ: {args.interval}s)...")
        while True:
            try:
                run_drift_check(min_samples=args.min_samples)
            except Exception as e:
                logger.error(f"Lỗi trong quá trình kiểm tra drift: {e}", exc_info=True)
            time.sleep(args.interval)
    else:
        run_drift_check(min_samples=args.min_samples)
