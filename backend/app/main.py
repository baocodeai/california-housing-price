import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import init_db
from backend.app.api.v1.router import api_router

# Định nghĩa các chỉ số đo lường Prometheus (Metrics)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Tổng số HTTP requests nhận được",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Thời gian xử lý HTTP request (giây)",
    ["method", "endpoint"],
)
INFERENCE_COUNT = Counter(
    "model_inference_total",
    "Tổng số lượt chạy suy luận dự đoán",
    ["model_version", "type"],
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Machine Learning chuẩn Production dự đoán giá nhà California",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_and_logging_middleware(request: Request, call_next):
    """Middleware tự động đo độ trễ, đếm request cho Prometheus và ghi Structured Log JSON."""
    start_time = time.perf_counter()
    method = request.method
    endpoint = request.url.path

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        logger.error(f"Lỗi máy chủ chưa được xử lý tại {method} {endpoint}: {e}", exc_info=True)
        raise e
    finally:
        latency = time.perf_counter() - start_time
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
        
        # Ghi log tóm tắt request
        logger.info(
            f"{method} {endpoint} -> {status_code} ({latency*1000:.2f}ms)"
        )

    return response


@app.on_event("startup")
async def startup_event():
    """Khởi tạo cơ sở dữ liệu và tải các dịch vụ khi máy chủ khởi động."""
    logger.info("Đang khởi tạo ứng dụng và cơ sở dữ liệu...")
    init_db()
    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} đã sẵn sàng nhận kết nối.")


@app.get("/prometheus-metrics", tags=["Observability"])
def prometheus_metrics():
    """
    Expose các chỉ số đo lường định dạng Prometheus phục vụ thu thập dữ liệu (scraping).
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Gắn các route của API v1
app.include_router(api_router, prefix=settings.API_V1_STR)
# Gắn route không prefix để tương thích ngược với Frontend
app.include_router(api_router)


@app.get("/", tags=["Health"])
def root_redirect():
    """Endpoint gốc kiểm tra trạng thái hoạt động của máy chủ."""
    from backend.app.services.model_service import model_service
    return {
        "title": settings.PROJECT_NAME,
        "status": "online",
        "version": settings.VERSION,
        "model_loaded": model_service.is_loaded(),
        "docs_url": "/docs",
    }
