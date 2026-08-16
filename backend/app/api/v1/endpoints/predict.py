"""
Các Endpoint xử lý dự đoán giá nhà đơn lẻ, dự đoán theo lô, xem lịch sử và dữ liệu phân tán.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from backend.app.schemas.housing import (
    HouseFeatures,
    SinglePredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    HistoryResponse,
    ScatterDataPoint,
)
from backend.app.services.model_service import model_service
from backend.app.db.session import save_prediction, get_prediction_history
from backend.app.core.logging import logger

router = APIRouter(tags=["Inference & History"])


@router.post("/predict", response_model=SinglePredictionResponse)
def predict_house_price(features: HouseFeatures):
    """
    Dự đoán giá trị nhà trung vị (California median house value) cho một căn nhà/khu vực đơn lẻ.
    Tự động ghi nhận lịch sử vào cơ sở dữ liệu.
    """
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mô hình chưa được nạp vào máy chủ. Vui lòng kiểm tra log khởi động.",
        )

    try:
        result = model_service.predict_single(features)
        
        # Lưu kết quả dự đoán vào cơ sở dữ liệu SQLite
        try:
            record = features.model_dump()
            record["predicted_price"] = result["predicted_price"]
            record["model_version"] = result["model_version"]
            record["created_at"] = result["timestamp"]
            save_prediction(record)
        except Exception as db_err:
            logger.error(f"Ghi lịch sử dự đoán thất bại: {db_err}")

        return SinglePredictionResponse(**result)
    except Exception as e:
        logger.error(f"Lỗi suy luận dự đoán: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suy luận thất bại: {str(e)}",
        )


@router.post("/predict-batch", response_model=BatchPredictionResponse)
def predict_batch_house_prices(request: BatchPredictionRequest):
    """
    Dự đoán giá nhà hàng loạt (Batch Prediction) lên tới 500 căn nhà trong 1 request duy nhất bằng vector hóa.
    """
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mô hình chưa được nạp vào máy chủ.",
        )

    try:
        result = model_service.predict_batch(request.items)
        return BatchPredictionResponse(**result)
    except Exception as e:
        logger.error(f"Lỗi suy luận hàng loạt: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dự đoán hàng loạt thất bại: {str(e)}",
        )


@router.get("/history", response_model=HistoryResponse)
def fetch_history(limit: int = 50):
    """
    Lấy danh sách các lượt dự đoán gần đây nhất được lưu trong cơ sở dữ liệu SQLite.
    """
    records = get_prediction_history(limit=limit)
    return HistoryResponse(
        total_records=len(records),
        history=records,
    )


@router.get("/scatter-data", response_model=List[ScatterDataPoint])
def fetch_scatter_data(sample_size: int = 100):
    """
    Trả về danh sách tọa độ điểm Actual vs Predicted để hiển thị biểu đồ đánh giá sai số trên giao diện người dùng.
    """
    if not model_service.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mô hình chưa được nạp.",
        )
    try:
        return model_service.get_scatter_data(sample_size=sample_size)
    except Exception as e:
        logger.error(f"Lỗi tạo dữ liệu biểu đồ phân tán: {e}")
        raise HTTPException(status_code=500, detail=str(e))
