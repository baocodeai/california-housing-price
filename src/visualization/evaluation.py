"""
Trực quan hóa đánh giá mô hình (Model Evaluation Visualizations):
Tạo biểu đồ so sánh Giá thực tế vs Giá dự đoán và biểu đồ phân phối sai số phần dư (Residuals),
lưu trữ trực tiếp các file ảnh vào reports/figures/.
"""
import argparse
import joblib
import numpy as np
from pathlib import Path

from src.config import MODEL_PATH, FIGURES_DIR
from src.data.dataloader import load_train_test_data
from src.data.build_features import FeatureEngineering

# Đăng ký FeatureEngineering cho unpickling
import __main__
__main__.FeatureEngineering = FeatureEngineering


def plot_actual_vs_predicted(
    model_path: Path = MODEL_PATH, output_dir: Path = FIGURES_DIR, sample_size: int = 500
):
    """
    Vẽ biểu đồ phân tán so sánh giữa Giá thực tế và Giá dự đoán trên tập kiểm thử độc lập.
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

    model = joblib.load(str(model_path))
    _, _, X_test, y_test = load_train_test_data()

    if len(X_test) > sample_size:
        indices = np.random.RandomState(42).choice(len(X_test), sample_size, replace=False)
        X_eval = X_test.iloc[indices]
        y_eval = y_test[indices]
    else:
        X_eval = X_test
        y_eval = y_test

    pred_log = model.predict(X_eval)
    preds = np.exp(pred_log)

    plt.figure(figsize=(8, 8))
    plt.scatter(y_eval, preds, alpha=0.4, color="#2ecc71", edgecolors="none", label="Dự đoán của mô hình")
    min_val = min(y_eval.min(), preds.min())
    max_val = max(y_eval.max(), preds.max())
    plt.plot([min_val, max_val], [min_val, max_val], "r--", lw=2, label="Đường dự đoán hoàn hảo (y=x)")

    plt.xlabel("Giá thực tế ($)", fontsize=12)
    plt.ylabel("Giá dự đoán ($)", fontsize=12)
    plt.title("So sánh Giá thực tế vs. Giá dự đoán (Holdout Test Set)", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)

    out_file = output_dir / "actual_vs_predicted.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[Visualization] Đã lưu biểu đồ Actual vs Predicted vào: {out_file}")


def plot_residuals(model_path: Path = MODEL_PATH, output_dir: Path = FIGURES_DIR):
    """
    Vẽ biểu đồ phân phối sai số phần dư (Residuals = Actual - Predicted).
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

    model = joblib.load(str(model_path))
    _, _, X_test, y_test = load_train_test_data()

    pred_log = model.predict(X_test)
    preds = np.exp(pred_log)
    residuals = y_test - preds

    plt.figure(figsize=(10, 6))
    plt.hist(residuals, bins=50, color="#e74c3c", edgecolor="black", alpha=0.7)
    plt.axvline(0, color="black", linestyle="--", lw=2)
    plt.xlabel("Sai số phần dư ($) = Giá thực tế - Giá dự đoán", fontsize=12)
    plt.ylabel("Tần suất", fontsize=12)
    plt.title("Phân phối sai số phần dư (Residuals Distribution)", fontsize=14)
    plt.grid(True, alpha=0.3)

    out_file = output_dir / "residuals_distribution.png"
    plt.savefig(out_file, dpi=150)
    plt.close()
    print(f"[Visualization] Đã lưu biểu đồ sai số phần dư vào: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo các hình ảnh đánh giá mô hình")
    parser.add_argument("-m", "--model", type=str, default=str(MODEL_PATH), help="Đường dẫn file artifact mô hình")
    parser.add_argument("-o", "--output-dir", type=str, default=str(FIGURES_DIR), help="Thư mục xuất file ảnh")
    args = parser.parse_args()

    plot_actual_vs_predicted(Path(args.model), Path(args.output_dir))
    plot_residuals(Path(args.model), Path(args.output_dir))
