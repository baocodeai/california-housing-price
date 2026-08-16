"""
Các Endpoint giám sát độ lệch phân phối dữ liệu (Data Drift Monitoring).
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from backend.app.services.drift_service import drift_service

router = APIRouter(tags=["Data Drift Monitoring"])


@router.get("/drift-status")
def get_drift_status_json():
    """
    Trả về dữ liệu JSON đo lường Data Drift phục vụ các hệ thống cảnh báo và giám sát tự động.
    """
    return drift_service.calculate_drift_metrics()


@router.get("/drift-report", response_class=HTMLResponse)
def get_drift_html_dashboard():
    """
    Render trực tiếp trang dashboard HTML phân tích trực quan mức độ Data Drift của từng đặc trưng.
    """
    html_content = drift_service.generate_drift_html_report()
    return HTMLResponse(content=html_content, status_code=200)
