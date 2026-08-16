import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.config import (
    CAT_COLS,
    LOG_NUM_COLS,
    N_GEO_CLUSTERS,
    NUM_COLS,
    RANDOM_SEED,
)


class FeatureEngineering(BaseEstimator, TransformerMixin):
    """
    Bộ biến đổi đặc trưng tùy chỉnh (Feature Engineering):
    - Chuẩn hóa phân loại vị trí biển ('ISLAND' chuyển thành 'NEAR OCEAN').
    - Tính toán các tỷ lệ nghiệp vụ: số phòng/hộ, số người/hộ, số phòng ngủ/tổng số phòng.
    - Phân cụm không gian bằng KMeans dựa trên tọa độ (kinh độ, vĩ độ).
    """

    def __init__(self, use_geo_cluster=True, n_geo_clusters=N_GEO_CLUSTERS, random_state=RANDOM_SEED):
        self.use_geo_cluster = use_geo_cluster
        self.n_geo_clusters = n_geo_clusters
        self.random_state = random_state
        self.kmeans_ = None

    def fit(self, X, y=None):
        """Học các tham số phân cụm KMeans từ tập dữ liệu huấn luyện."""
        df = X.copy()
        if self.use_geo_cluster and len(df) >= self.n_geo_clusters:
            self.kmeans_ = KMeans(
                n_clusters=self.n_geo_clusters,
                random_state=self.random_state,
                n_init=10,
            )
            self.kmeans_.fit(df[["longitude", "latitude"]])
        return self

    def transform(self, X):
        """Áp dụng biến đổi đặc trưng lên dữ liệu."""
        df = X.copy()
        df["ocean_proximity"] = df["ocean_proximity"].replace("ISLAND", "NEAR OCEAN")

        households = df["households"].replace(0, 1)
        total_rooms = df["total_rooms"].replace(0, 1)

        # Tính toán các tỷ lệ đặc trưng mới
        df["rooms_per_household"] = df["total_rooms"] / households
        df["population_per_household"] = df["population"] / households
        df["bedrooms_per_room"] = df["total_bedrooms"] / total_rooms

        # Gán nhãn cụm địa lý nếu có
        if self.use_geo_cluster and self.kmeans_ is not None:
            labels = self.kmeans_.predict(df[["longitude", "latitude"]])
            df["geo_cluster"] = labels.astype(str)
        else:
            df["geo_cluster"] = "0"

        return df


def build_preprocessor() -> ColumnTransformer:
    """
    Xây dựng ColumnTransformer để xử lý dữ liệu:
    - log_num: Điền khuyết, biến đổi log(1+x), chuẩn hóa StandardScaler.
    - num: Điền khuyết trung vị, chuẩn hóa StandardScaler.
    - cat: Mã hóa One-Hot Encoding cho các biến phân loại.
    """
    log_num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("log", FunctionTransformer(np.log1p, validate=False)),
        ("scaler", StandardScaler()),
    ])

    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    cat_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer([
        ("log_num", log_num_pipeline, LOG_NUM_COLS),
        ("num", num_pipeline, NUM_COLS),
        ("cat", cat_pipeline, CAT_COLS),
    ])


def build_full_pipeline(estimator) -> Pipeline:
    """
    Đóng gói toàn bộ quy trình: FeatureEngineering -> Preprocessing -> Model vào một Pipeline duy nhất.
    """
    return Pipeline([
        ("feat_eng", FeatureEngineering()),
        ("preprocess", build_preprocessor()),
        ("model", estimator),
    ])
