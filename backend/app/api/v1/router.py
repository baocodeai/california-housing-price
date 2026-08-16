"""
Router tổng hợp cho API v1: Gom các module endpoints (health, predict, metrics, drift, enrichment).
"""
from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, predict, metrics, drift, enrichment

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(predict.router)
api_router.include_router(metrics.router)
api_router.include_router(drift.router)
api_router.include_router(enrichment.router, prefix="/enrichment", tags=["Enrichment"])
