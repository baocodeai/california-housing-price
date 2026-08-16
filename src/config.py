import os
from pathlib import Path

# Đường dẫn thư mục gốc của dự án
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
CONFIGS_DIR = PROJECT_ROOT / "configs"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Đường dẫn các tập dữ liệu
RAW_DATA_PATH = DATA_DIR / "raw" / "housing.csv"
DATA_PATH = RAW_DATA_PATH  # Tên định danh tương thích ngược
INTERIM_DATA_PATH = DATA_DIR / "interim" / "housing_cleaned.csv"
PROCESSED_TRAIN_PATH = DATA_DIR / "processed" / "train.csv"
PROCESSED_TEST_PATH = DATA_DIR / "processed" / "test.csv"
EXTERNAL_DATA_PATH = DATA_DIR / "external" / "sample_houses.json"

# Đường dẫn lưu trữ Artifacts & Mô hình
MODEL_PATH = MODELS_DIR / "stacking_pipeline.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"
MLRUNS_DIR = MODELS_DIR / "mlruns"

# Các siêu tham số huấn luyện mặc định
RANDOM_SEED = 42
TEST_SIZE = 0.2
N_GEO_CLUSTERS = 10

# Định nghĩa các cột đặc trưng trong tập dữ liệu
TARGET_COL = "median_house_value"  # Cột mục tiêu: giá nhà trung vị
LOG_NUM_COLS = ["total_rooms", "total_bedrooms", "households", "population"]  # Các cột biến đổi log
NUM_COLS = [
    "longitude",
    "latitude",
    "housing_median_age",
    "median_income",
    "rooms_per_household",
    "population_per_household",
    "bedrooms_per_room",
]  # Các cột số liên tục
CAT_COLS = ["ocean_proximity", "geo_cluster"]  # Các cột phân loại
RAW_FEATURE_COLS = [
    "longitude",
    "latitude",
    "housing_median_age",
    "total_rooms",
    "total_bedrooms",
    "population",
    "households",
    "median_income",
    "ocean_proximity",
]  # 9 đặc trưng đầu vào gốc
