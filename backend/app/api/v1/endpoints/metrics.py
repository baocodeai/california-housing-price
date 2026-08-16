"""
Các Endpoint trả về dữ liệu so sánh hiệu năng các mô hình và metadata của mô hình đang triển khai.
"""
import os
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.core.config import settings

router = APIRouter(tags=["Model Benchmarks & Metrics"])


@router.get("/metrics")
def get_model_benchmarks():
    """
    Trả về bảng so sánh đối chuẩn (Benchmark Comparison) giữa các thuật toán mô hình khác nhau.
    """
    csv_path = settings.BASE_DIR / "model_comparison.csv"
    if not csv_path.exists():
        csv_path = settings.BASE_DIR / "reports" / "model_comparison.csv"

    if not csv_path.exists():
        raise HTTPException(
            status_code=404, detail="Không tìm thấy file so sánh đối chuẩn model_comparison.csv"
        )

    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


@router.get("/model-metadata")
def get_current_model_metadata():
    """
    Trả về thông tin metadata chi tiết của mô hình đang được triển khai (phiên bản, tham số, metrics).
    """
    from backend.app.services.model_service import model_service
    return {
        "is_loaded": model_service.is_loaded(),
        "version": model_service.version,
        "metadata": model_service.metadata,
    }
