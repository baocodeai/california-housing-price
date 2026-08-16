"""
Dịch vụ Feature Store không gian địa lý và Tự động làm giàu đặc trưng (Geospatial Enrichment Service).
Sử dụng cấu trúc cây không gian KDTree trên tập dữ liệu điều tra dân số California để thực hiện
truy vấn tìm láng giềng gần nhất (Nearest Neighbors) theo tọa độ (vĩ độ, kinh độ) với độ trễ cực thấp (< 1ms).
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.spatial import KDTree
from src.config import DATA_PATH
from backend.app.core.logging import logger


class GeospatialEnrichmentService:
    """
    Feature Store không gian địa lý hỗ trợ tự động điền các thông tin đặc trưng khi người dùng chọn điểm trên bản đồ.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeospatialEnrichmentService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info(f"Đang khởi tạo Geospatial Feature Store từ {DATA_PATH}...")
        if not DATA_PATH.exists():
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu tại {DATA_PATH}")

        self.df = pd.read_csv(DATA_PATH)
        # Điền khuyết total_bedrooms bằng trung vị
        self.df['total_bedrooms'] = self.df['total_bedrooms'].fillna(self.df['total_bedrooms'].median())
        
        # Xây dựng chỉ mục cây không gian KDTree dựa trên [latitude, longitude]
        coords = self.df[['latitude', 'longitude']].values
        self.tree = KDTree(coords)
        logger.info(f"Chỉ mục KDTree không gian đã dựng thành công với {len(self.df)} block dân số.")

    def lookup_nearest_block(self, latitude: float, longitude: float) -> dict:
        """
        Truy vấn block điều tra dân số gần nhất tại California dựa theo cặp tọa độ (lat, lng).
        Trả về các đặc trưng nhân khẩu học và nhà ở để tự động điền vào biểu mẫu.
        """
        query_coord = np.array([latitude, longitude])
        dist, idx = self.tree.query(query_coord)

        matched_row = self.df.iloc[idx]

        # Ước lượng khoảng cách xấp xỉ theo km: 1 độ ~ 111 km
        approx_km = round(dist * 111.0, 2)

        return {
            "latitude": float(matched_row["latitude"]),
            "longitude": float(matched_row["longitude"]),
            "housing_median_age": float(matched_row["housing_median_age"]),
            "total_rooms": float(matched_row["total_rooms"]),
            "total_bedrooms": float(matched_row["total_bedrooms"]),
            "population": float(matched_row["population"]),
            "households": float(matched_row["households"]),
            "median_income": float(matched_row["median_income"]),
            "ocean_proximity": str(matched_row["ocean_proximity"]),
            "lookup_distance_km": approx_km,
            "matched_block_index": int(idx),
        }


enrichment_service = GeospatialEnrichmentService()
