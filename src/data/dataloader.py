"""
Tiện ích nạp dữ liệu (Data Loader):
Đọc các tập Train/Test từ đĩa và chuẩn bị sẵn ma trận đặc trưng (X) cùng vector mục tiêu (y).
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple

from src.config import (
    PROCESSED_TRAIN_PATH,
    PROCESSED_TEST_PATH,
    RAW_DATA_PATH,
    RAW_FEATURE_COLS,
    TARGET_COL,
)
from src.data.splitting import split_and_save_data


def load_train_test_data(
    train_path: Path = PROCESSED_TRAIN_PATH,
    test_path: Path = PROCESSED_TEST_PATH,
    log_target: bool = True,
) -> Tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray]:
    """
    Trả về bộ dữ liệu (X_train, y_train, X_test, y_test).
    Nếu chưa có file trong processed, hàm sẽ tự động gọi kịch bản chia tách từ dữ liệu thô.
    """
    train_path = Path(train_path)
    test_path = Path(test_path)

    if not train_path.exists() or not test_path.exists():
        print(f"[DataLoader] Chưa tìm thấy file processed. Đang tự động chia từ {RAW_DATA_PATH}...")
        train_df, test_df = split_and_save_data(RAW_DATA_PATH, train_path, test_path)
    else:
        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)

    X_train = train_df[RAW_FEATURE_COLS]
    y_train = np.log(train_df[TARGET_COL].values) if log_target else train_df[TARGET_COL].values

    X_test = test_df[RAW_FEATURE_COLS]
    y_test = test_df[TARGET_COL].values

    return X_train, y_train, X_test, y_test
