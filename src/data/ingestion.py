"""
Kịch bản thu thập và kiểm tra dữ liệu đầu vào (Data Ingestion):
Đọc tập dữ liệu thô, xác thực các trường bắt buộc và kiểm tra tính toàn vẹn của file.
"""
import argparse
import sys
import pandas as pd
from pathlib import Path
from src.config import RAW_DATA_PATH, RAW_FEATURE_COLS, TARGET_COL


def load_raw_data(data_path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """
    Tải dữ liệu thô dạng CSV và kiểm tra sự hiện diện của đầy đủ các cột bắt buộc.
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu thô tại: {data_path.resolve()}")

    df = pd.read_csv(data_path)
    required_cols = RAW_FEATURE_COLS + [TARGET_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dữ liệu bị thiếu các cột bắt buộc: {missing_cols}")

    print(f"[Ingestion] Đã nạp thành công dữ liệu thô từ {data_path} với kích thước {df.shape}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thu thập và xác thực dữ liệu thô California Housing")
    parser.add_argument("-r", "--raw-path", type=str, default=str(RAW_DATA_PATH), help="Đường dẫn đến file dữ liệu thô")
    args = parser.parse_args()

    try:
        df = load_raw_data(args.raw_path)
        print(f"Thông tin tổng quát:\n{df.info()}")
    except Exception as e:
        print(f"Lỗi Ingestion: {e}", file=sys.stderr)
        sys.exit(1)
