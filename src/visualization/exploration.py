"""
Trực quan hóa khám phá dữ liệu (Exploratory Data Analysis - EDA):
Tạo các biểu đồ phân bố đặc trưng, bản đồ nhiệt giá nhà theo địa lý và mật độ dân số,
sau đó lưu trữ các hình ảnh vào thư mục reports/figures/.
"""
import argparse
from pathlib import Path
import pandas as pd

from src.config import RAW_DATA_PATH, FIGURES_DIR


def plot_feature_distributions(data_path: Path = RAW_DATA_PATH, output_dir: Path = FIGURES_DIR):
    """
    Vẽ biểu đồ histogram phân phối tần suất của các đặc trưng dạng số.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[Visualization] Thư viện matplotlib chưa được cài đặt. Bỏ qua vẽ biểu đồ.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    df.hist(bins=50, figsize=(16, 12), color="#3498db", edgecolor="black")
    plt.suptitle("Phân phối các đặc trưng dữ liệu California Housing", fontsize=16)
    plt.tight_layout()

    out_file = output_dir / "feature_distributions.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[Visualization] Đã lưu biểu đồ phân phối đặc trưng vào: {out_file}")


def plot_geographical_distribution(data_path: Path = RAW_DATA_PATH, output_dir: Path = FIGURES_DIR):
    """
    Vẽ biểu đồ phân tán địa lý thể hiện giá nhà và mật độ dân cư tại California.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[Visualization] Thư viện matplotlib chưa được cài đặt. Bỏ qua vẽ biểu đồ.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        df["longitude"],
        df["latitude"],
        c=df["median_house_value"],
        cmap=plt.get_cmap("jet"),
        s=df["population"] / 100,
        alpha=0.4,
        label="Dân số / 100",
    )
    plt.colorbar(scatter, label="Giá trị nhà trung vị ($)")
    plt.xlabel("Kinh độ (Longitude)")
    plt.ylabel("Vĩ độ (Latitude)")
    plt.title("Bản đồ phân bổ giá nhà & mật độ dân cư California", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)

    out_file = output_dir / "geographical_distribution.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[Visualization] Đã lưu biểu đồ phân bổ địa lý vào: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo các hình ảnh trực quan hóa EDA")
    parser.add_argument("-d", "--data", type=str, default=str(RAW_DATA_PATH), help="Đường dẫn file dữ liệu đầu vào")
    parser.add_argument("-o", "--output-dir", type=str, default=str(FIGURES_DIR), help="Thư mục xuất file ảnh")
    args = parser.parse_args()

    plot_feature_distributions(Path(args.data), Path(args.output_dir))
    plot_geographical_distribution(Path(args.data), Path(args.output_dir))
