"""
Pipeline huấn luyện mô hình Stacking Regressor:
Tự động hóa hoàn toàn theo cấu hình YAML, đánh giá hiệu năng trên tập kiểm thử,
lưu trữ artifact mô hình dạng joblib và hỗ trợ theo dõi với MLflow.
"""
import argparse
import json
import time
import joblib
import numpy as np
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from sklearn.pipeline import Pipeline

from src.config import (
    MODEL_PATH,
    METADATA_PATH,
    MODELS_DIR,
    RAW_FEATURE_COLS,
    TARGET_COL,
)
from src.data.dataloader import load_train_test_data
from src.models.evaluate import calculate_metrics, print_evaluation_report
from src.models.stacking.model import build_stacking_pipeline


def train_stacking_model(
    config_path: Optional[str] = "configs/stacking.yaml",
    config_dict: Optional[Dict[str, Any]] = None,
) -> Tuple[Pipeline, Dict[str, float]]:
    """
    Thực thi quy trình huấn luyện mô hình Stacking dựa trên cấu hình YAML.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Tải cấu hình
    cfg: Dict[str, Any] = {}
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print(f"[Training] Đã nạp cấu hình từ: {config_path}")
    if config_dict:
        cfg.update(config_dict)

    # 2. Tham số dữ liệu
    data_cfg = cfg.get("data", {})
    train_path = Path(data_cfg.get("train_path", "data/processed/train.csv"))
    test_path = Path(data_cfg.get("test_path", "data/processed/test.csv"))
    log_target = data_cfg.get("log_target", True)

    print(f"[Training] Đang nạp dữ liệu (train={train_path}, test={test_path})...")
    X_train, y_train_target, X_test, y_test = load_train_test_data(
        train_path=train_path,
        test_path=test_path,
        log_target=log_target,
    )
    print(f"[Training] Dữ liệu đã sẵn sàng: Train={len(X_train)} mẫu, Test={len(X_test)} mẫu.")

    # 3. Khởi tạo pipeline từ cấu hình
    print("[Training] Đang khởi tạo pipeline Stacking từ cấu hình...")
    pipeline = build_stacking_pipeline(config=cfg)

    # 4. Huấn luyện mô hình
    start_time = time.time()
    print("[Training] Đang khớp mô hình Stacking Regressor...")
    pipeline.fit(X_train, y_train_target)
    training_duration = time.time() - start_time
    print(f"[Training] Huấn luyện thành công trong {training_duration:.2f} giây.")

    # 5. Đánh giá trên tập test độc lập
    print("[Training] Đang đánh giá hiệu năng trên tập kiểm thử (Test set)...")
    pred_raw = pipeline.predict(X_test)
    pred_values = np.exp(pred_raw) if log_target else pred_raw

    metrics = calculate_metrics(y_test, pred_values)
    model_name = cfg.get("model", {}).get("name", "Stacking Regressor (Production)")
    print_evaluation_report(metrics, model_name=model_name)

    # 6. Lưu trữ Artifacts
    out_model_path = Path(cfg.get("model", {}).get("output_model_path", str(MODEL_PATH)))
    out_meta_path = Path(cfg.get("model", {}).get("output_metadata_path", str(METADATA_PATH)))
    out_model_path.parent.mkdir(parents=True, exist_ok=True)
    out_meta_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Training] Đang xuất file mô hình ra {out_model_path}...")
    joblib.dump(pipeline, out_model_path, compress=3)

    metadata = {
        "model_name": model_name,
        "model_version": cfg.get("model", {}).get("version", "1.0.0"),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "training_duration_seconds": round(training_duration, 2),
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "metrics": metrics,
        "input_features": RAW_FEATURE_COLS,
        "target": TARGET_COL,
        "config": cfg,
    }

    with open(out_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Training] Đã lưu metadata mô hình ra {out_meta_path}")

    # 7. Ghi nhận nhật ký MLflow nếu được bật
    mlflow_cfg = cfg.get("mlflow", {})
    if mlflow_cfg.get("enabled", False):
        try:
            import mlflow
            mlflow.set_tracking_uri(mlflow_cfg.get("tracking_uri", "models/mlruns"))
            mlflow.set_experiment(mlflow_cfg.get("experiment_name", "california_housing_stacking"))
            with mlflow.start_run(run_name=f"train_{metadata['model_version']}"):
                mlflow.log_params({
                    "cv": cfg.get("stacking", {}).get("cv", 3),
                    "svr_C": cfg.get("base_models", {}).get("svr", {}).get("C", 30.0),
                    "rf_n_estimators": cfg.get("base_models", {}).get("random_forest", {}).get("n_estimators", 300),
                })
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(out_model_path))
                print("[Training] Đã ghi nhận run và artifacts vào MLflow.")
        except Exception as e:
            print(f"[Training] Bỏ qua MLflow (hoặc lỗi kết nối): {e}")

    return pipeline, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình Stacking Regressor")
    parser.add_argument("-c", "--config", type=str, default="configs/stacking.yaml", help="Đường dẫn file cấu hình YAML")
    args = parser.parse_args()

    train_stacking_model(config_path=args.config)
