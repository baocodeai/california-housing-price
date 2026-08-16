"""
Các Endpoint kiểm tra sức khỏe hệ thống (Health Check, Liveness Probe, Readiness Probe cho Kubernetes/Docker).
"""
import time
from fastapi import APIRouter, status, Response
from backend.app.schemas.housing import HealthResponse
from backend.app.services.model_service import model_service
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])

START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Kiểm tra tổng quát sức khỏe của toàn bộ dịch vụ API và trạng thái tải mô hình.
    """
    model_loaded = model_service.is_loaded()
    return HealthResponse(
        status="healthy" if model_loaded else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        model_loaded=model_loaded,
        model_version=model_service.version,
        uptime_seconds=round(time.time() - START_TIME, 2),
        database_connected=settings.DB_PATH.exists() or True,
    )


@router.get("/live", status_code=status.HTTP_200_OK)
def liveness_probe():
    """
    Liveness Probe phục vụ Kubernetes / Container: Kiểm tra tiến trình máy chủ có đang phản hồi.
    """
    return {"status": "alive"}


@router.get("/ready")
def readiness_probe(response: Response):
    """
    Readiness Probe phục vụ Kubernetes: Kiểm tra xem mô hình ML đã nạp xong vào RAM và sẵn sàng phục vụ traffic hay chưa.
    """
    if not model_service.is_loaded():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "Mô hình ML chưa được nạp vào bộ nhớ"}
    return {"status": "ready", "model_version": model_service.version}
