"""
Kịch bản làm sạch dữ liệu (Data Cleaning):
Xử lý dữ liệu bị khuyết thiếu (missing values), lọc các giá trị dị biệt (outliers),
và xuất dữ liệu trung gian ra thư mục data/interim/.
"""
import argparse
import sys
import pandas as pd
from pathlib import Path
from src.config import RAW_DATA_PATH, INTERIM_DATA_PATH


def clean_housing_data(
    input_path: Path = RAW_DATA_PATH,
    output_path: Path = INTERIM_DATA_PATH,
    impute_bedrooms: bool = True,
    filter_capped: bool = False,
) -> pd.DataFrame:
    """
    Làm sạch dữ liệu nhà ở và xuất ra file CSV trung gian (interim).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Cleaning] Đang đọc dữ liệu từ {input_path}...")
    df = pd.read_csv(input_path)

    initial_len = len(df)
    null_bedrooms = df["total_bedrooms"].isnull().sum()
    print(f"[Cleaning] Phát hiện {null_bedrooms} giá trị rỗng trong cột total_bedrooms.")

    if impute_bedrooms:
        median_bedrooms = df["total_bedrooms"].median()
        df["total_bedrooms"] = df["total_bedrooms"].fillna(median_bedrooms)
        print(f"[Cleaning] Đã điền khuyết total_bedrooms bằng giá trị trung vị: {median_bedrooms}")
    else:
        df = df.dropna(subset=["total_bedrooms"])
        print(f"[Cleaning] Đã xóa các hàng bị khuyết total_bedrooms: {initial_len - len(df)} hàng đã bị loại.")

    if filter_capped:
        # Lọc các dòng bị giới hạn trần (capped) về tuổi nhà và giá trị
        df = df[(df["housing_median_age"] < 52) & (df["median_house_value"] < 500000)]
        print(f"[Cleaning] Đã lọc các giá trị bị trần: còn lại {len(df)} mẫu.")

    df.to_csv(output_path, index=False)
    print(f"[Cleaning] Đã xuất dữ liệu sạch ra {output_path} ({len(df)} bản ghi).")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Làm sạch dữ liệu nhà ở California")
    parser.add_argument("-i", "--input", type=str, default=str(RAW_DATA_PATH), help="Đường dẫn file dữ liệu thô")
    parser.add_argument("-o", "--output", type=str, default=str(INTERIM_DATA_PATH), help="Đường dẫn file đầu ra interim")
    parser.add_argument("--filter-capped", action="store_true", help="Lọc các bản ghi bị trần tuổi/giá")
    args = parser.parse_args()

    clean_housing_data(args.input, args.output, filter_capped=args.filter_capped)
