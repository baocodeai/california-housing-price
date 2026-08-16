"""
Kịch bản chia tách tập dữ liệu (Data Splitting):
Chia tập dữ liệu thành 2 phần Train và Test có thể tái lập (reproducible),
sau đó lưu trữ trực tiếp vào thư mục data/processed/.
"""
import argparse
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from src.config import (
    RAW_DATA_PATH,
    PROCESSED_TRAIN_PATH,
    PROCESSED_TEST_PATH,
    RANDOM_SEED,
    TEST_SIZE,
)


def split_and_save_data(
    input_path: Path = RAW_DATA_PATH,
    train_path: Path = PROCESSED_TRAIN_PATH,
    test_path: Path = PROCESSED_TEST_PATH,
    test_size: float = TEST_SIZE,
    random_seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tải dữ liệu, chia tách thành 2 tập Train và Test, lưu vào thư mục data/processed.
    """
    input_path = Path(input_path)
    train_path = Path(train_path)
    test_path = Path(test_path)

    train_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Splitting] Đang đọc dữ liệu từ {input_path}...")
    df = pd.read_csv(input_path)

    train_df, test_df = train_test_split(
        df, test_size=test_size, random_state=random_seed
    )

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"[Splitting] Tập Train ({len(train_df)} dòng) đã lưu tại: {train_path}")
    print(f"[Splitting] Tập Test ({len(test_df)} dòng) đã lưu tại: {test_path}")

    return train_df, test_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chia dữ liệu nhà ở thành tập Train và Test")
    parser.add_argument("-i", "--input", type=str, default=str(RAW_DATA_PATH), help="Đường dẫn file đầu vào")
    parser.add_argument("--train-path", type=str, default=str(PROCESSED_TRAIN_PATH), help="Đường dẫn file Train đầu ra")
    parser.add_argument("--test-path", type=str, default=str(PROCESSED_TEST_PATH), help="Đường dẫn file Test đầu ra")
    parser.add_argument("--test-size", type=float, default=TEST_SIZE, help="Tỷ lệ tập Test")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    args = parser.parse_args()

    split_and_save_data(
        args.input, args.train_path, args.test_path, args.test_size, args.seed
    )
