"""
Quản lý kết nối cơ sở dữ liệu SQLite và lưu trữ lịch sử các lượt dự đoán.
"""
import sqlite3
import os
from typing import List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger

_db_initialized = False


def init_db():
    """
    Khởi tạo bảng cơ sở dữ liệu nếu chưa tồn tại.
    """
    global _db_initialized
    os.makedirs(settings.DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH))
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                longitude REAL NOT NULL,
                latitude REAL NOT NULL,
                housing_median_age REAL NOT NULL,
                total_rooms REAL NOT NULL,
                total_bedrooms REAL NOT NULL,
                population REAL NOT NULL,
                households REAL NOT NULL,
                median_income REAL NOT NULL,
                ocean_proximity TEXT NOT NULL,
                predicted_price REAL NOT NULL,
                model_version TEXT DEFAULT '1.0.0',
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at)
        """)
        conn.commit()
        _db_initialized = True
    except Exception as e:
        logger.error(f"Khởi tạo cơ sở dữ liệu thất bại: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def get_db_connection():
    """
    Trả về một kết nối cơ sở dữ liệu SQLite với chế độ Row Factory.
    Đảm bảo schema bảng luôn được khởi tạo trước.
    """
    global _db_initialized
    if not _db_initialized:
        init_db()
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def save_prediction(record: Dict[str, Any]) -> int:
    """
    Lưu một bản ghi kết quả dự đoán vào cơ sở dữ liệu SQLite.
    """
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO predictions (
                longitude, latitude, housing_median_age, total_rooms, total_bedrooms,
                population, households, median_income, ocean_proximity, predicted_price,
                model_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["longitude"],
            record["latitude"],
            record["housing_median_age"],
            record["total_rooms"],
            record["total_bedrooms"],
            record["population"],
            record["households"],
            record["median_income"],
            record["ocean_proximity"],
            record["predicted_price"],
            record.get("model_version", "1.0.0"),
            record["created_at"],
        ))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def get_prediction_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các lượt dự đoán gần đây nhất từ cơ sở dữ liệu.
    """
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
