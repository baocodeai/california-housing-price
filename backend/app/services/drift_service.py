"""
Dịch vụ phát hiện Data Drift giữa tập dữ liệu cơ sở và các lượt dự đoán thực tế trên môi trường Production.
Sử dụng kiểm định thống kê Kolmogorov-Smirnov (KS-Test) hai mẫu.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from scipy.stats import ks_2samp

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import get_db_connection


class DriftService:
    """
    Dịch vụ phát hiện sự sai lệch phân phối (Data Drift) giữa tập huấn luyện và dữ liệu thực tế.
    """
    def __init__(self):
        self.ref_data: Optional[pd.DataFrame] = None
        self._load_reference_data()

    def _load_reference_data(self):
        try:
            if settings.DATA_PATH.exists():
                self.ref_data = pd.read_csv(settings.DATA_PATH).dropna()
                logger.info(f"Đã nạp tập dữ liệu cơ sở gồm {len(self.ref_data)} mẫu.")
        except Exception as e:
            logger.error(f"Nạp dữ liệu cơ sở thất bại: {e}", exc_info=True)

    def calculate_drift_metrics(self) -> Dict[str, Any]:
        """
        Chạy kiểm định KS-Test hai mẫu trên từng đặc trưng số liên tục.
        """
        if self.ref_data is None:
            self._load_reference_data()
            if self.ref_data is None:
                return {"error": "Dữ liệu cơ sở tham chiếu không khả dụng."}

        conn = get_db_connection()
        try:
            curr_df = pd.read_sql_query("SELECT * FROM predictions", conn)
        finally:
            conn.close()

        if len(curr_df) < 5:
            return {
                "status": "insufficient_data",
                "message": f"Cần ít nhất 5 bản ghi trong lịch sử để tính toán độ lệch. Hiện có: {len(curr_df)}",
                "sample_count": len(curr_df),
            }

        features_num = [
            "longitude", "latitude", "housing_median_age", "total_rooms",
            "total_bedrooms", "population", "households", "median_income"
        ]

        feature_results = []
        drift_count = 0

        for f in features_num:
            ref_vals = self.ref_data[f].astype(float).values
            curr_vals = curr_df[f].astype(float).values

            stat, p_value = ks_2samp(ref_vals, curr_vals)
            is_drift = bool(p_value < 0.05)
            if is_drift:
                drift_count += 1

            feature_results.append({
                "feature": f,
                "ref_mean": round(float(np.mean(ref_vals)), 4),
                "current_mean": round(float(np.mean(curr_vals)), 4),
                "ks_statistic": round(float(stat), 4),
                "p_value": round(float(p_value), 6),
                "drift_detected": is_drift,
            })

        return {
            "status": "success",
            "total_features_tested": len(features_num),
            "drifted_features_count": drift_count,
            "overall_drift_detected": drift_count > 0,
            "current_sample_size": len(curr_df),
            "feature_metrics": feature_results,
        }

    def generate_drift_html_report(self) -> str:
        """
        Tạo báo cáo giao diện HTML trực quan xem trực tiếp trên trình duyệt.
        """
        drift_data = self.calculate_drift_metrics()
        
        if drift_data.get("status") == "insufficient_data":
            return f"""
            <html>
            <body style="background:#0b0c10;color:#c5c6c7;font-family:sans-serif;padding:40px;text-align:center;">
                <h2>⚠️ Chưa đủ bản ghi lịch sử dự đoán</h2>
                <p>{drift_data.get('message')}</p>
            </body>
            </html>
            """

        feature_rows = ""
        for item in drift_data.get("feature_metrics", []):
            drift_class = "drift-yes" if item["drift_detected"] else "drift-no"
            drift_label = "CÓ TRÔI DẠT (DRIFT)" if item["drift_detected"] else "BÌNH THƯỜNG"
            feature_rows += f"""
            <tr>
                <td><strong>{item['feature']}</strong></td>
                <td>{item['ref_mean']:.4f}</td>
                <td>{item['current_mean']:.4f}</td>
                <td>{item['ks_statistic']:.4f}</td>
                <td>{item['p_value']:.4e}</td>
                <td class="{drift_class}">{drift_label}</td>
            </tr>
            """

        overall = drift_data.get("overall_drift_detected", False)
        status_color = "#f28b82" if overall else "#81c995"
        status_text = "PHÁT HIỆN DATA DRIFT" if overall else "BÌNH THƯỜNG (KHÔNG CÓ DRIFT)"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Báo cáo Data Drift - California Housing</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0b0c10; color: #c5c6c7; padding: 40px; margin: 0; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                h1 {{ color: #66fcf1; border-bottom: 2px solid #45a29e; padding-bottom: 12px; margin-bottom: 24px; }}
                .badge {{ display: inline-block; padding: 6px 14px; border-radius: 6px; font-weight: bold; background: {status_color}; color: #0b0c10; font-size: 1.1rem; }}
                .card {{ background: #1f2833; padding: 20px; border-radius: 8px; margin-bottom: 24px; border: 1px solid #45a29e33; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
                th, td {{ border: 1px solid #45a29e33; padding: 12px; text-align: left; font-size: 0.95rem; }}
                th {{ background: #141c24; color: #66fcf1; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }}
                tr:hover {{ background: #2b3846; }}
                .drift-yes {{ color: #f28b82; font-weight: bold; }}
                .drift-no {{ color: #81c995; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 0.85rem; color: #888; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Báo cáo Giám sát Data Drift Production</h1>
                <div class="card">
                    <p>Trạng thái: <span class="badge">{status_text}</span></p>
                    <p>Tổng số request production được theo dõi: <strong>{drift_data.get('current_sample_size', 0)}</strong></p>
                    <p>Số đặc trưng bị trôi dạt: <strong>{drift_data.get('drifted_features_count', 0)} / {drift_data.get('total_features_tested', 0)}</strong></p>
                    <p>Kiểm định thống kê: <strong>Kolmogorov-Smirnov (KS) Two-Sample Test (α = 0.05)</strong></p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Tên đặc trưng</th>
                            <th>Trung bình cơ sở (Reference)</th>
                            <th>Trung bình hiện tại (Production)</th>
                            <th>KS Statistic</th>
                            <th>P-Value</th>
                            <th>Trạng thái Drift</th>
                        </tr>
                    </thead>
                    <tbody>
                        {feature_rows}
                    </tbody>
                </table>
                <div class="footer">California Housing Price MLOps Monitoring System</div>
            </div>
        </body>
        </html>
        """
        return html


drift_service = DriftService()
