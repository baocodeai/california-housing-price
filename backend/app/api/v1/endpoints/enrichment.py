"""
Endpoint tra cứu và tự động làm giàu đặc trưng không gian địa lý (Enrichment API).
"""
from fastapi import APIRouter, Query, HTTPException, status
from backend.app.services.enrichment_service import enrichment_service
from backend.app.core.logging import logger

router = APIRouter()


@router.get("/lookup", status_code=status.HTTP_200_OK, summary="Tra cứu đặc trưng của block dân cư gần nhất")
def lookup_location_features(
    latitude: float = Query(..., ge=32.0, le=42.0, description="Vĩ độ trong phạm vi California"),
    longitude: float = Query(..., ge=-125.0, le=-114.0, description="Kinh độ trong phạm vi California"),
):
    """
    Trả về các thông tin nhân khẩu học và đặc trưng nhà ở từ block điều tra dân số gần nhất
    để tự động điền vào form dự đoán khi người dùng chấm điểm trên bản đồ.
    """
    try:
        enriched_data = enrichment_service.lookup_nearest_block(latitude, longitude)
        return {
            "status": "success",
            "features": enriched_data,
        }
    except Exception as e:
        logger.error(f"Lỗi tra cứu đặc trưng địa lý: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tra cứu đặc trưng vị trí thất bại: {str(e)}",
        )
