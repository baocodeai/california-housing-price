"""
Cấu hình hệ thống ghi log có cấu trúc (Structured JSON Logging) phục vụ giám sát Production.
"""
import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Định dạng các bản ghi log thành chuỗi JSON chuẩn hóa phục vụ các hệ thống
    quan sát tập trung (như Grafana Loki, ELK Stack, hoặc AWS CloudWatch).
    """
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        
        if hasattr(record, "trace_id"):
            log_object["trace_id"] = record.trace_id
        if hasattr(record, "latency_ms"):
            log_object["latency_ms"] = record.latency_ms
        if hasattr(record, "endpoint"):
            log_object["endpoint"] = record.endpoint
            
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_object, ensure_ascii=False)


def setup_logger(name: str = "california_housing") -> logging.Logger:
    """Khởi tạo và cấu hình logger với JSONFormatter xuất ra luồng stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger


logger = setup_logger()
