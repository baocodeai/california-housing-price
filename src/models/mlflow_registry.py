"""
Tích hợp MLflow Model Registry & Theo dõi thí nghiệm (Experiment Tracking) cho Pipeline California Housing.
Bao gồm:
- Tự động log siêu tham số, dữ liệu metadata, và các chỉ số đánh giá.
- Ràng buộc cấu trúc dữ liệu đầu vào/ra với MLflow Model Signature.
- Đăng ký mô hình vào MLflow Model Registry.
- Chuyển đổi trạng thái mô hình (Staging -> Production -> Archived) hoặc gán alias (Champion/Challenger).
"""
import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.models.signature import infer_signature
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from src.config import (
    DATA_PATH,
    MODEL_PATH,
    METADATA_PATH,
    MODELS_DIR,
    RANDOM_SEED,
    RAW_FEATURE_COLS,
    TARGET_COL,
    TEST_SIZE,
)
from src.data.build_features import FeatureEngineering, build_preprocessor
from src.models.stacking.model import build_stacking_pipeline
from src.data.dataloader import load_train_test_data
from src.models.evaluate import calculate_metrics, print_evaluation_report


def train_and_register_with_mlflow(
    experiment_name: str = "California_Housing_Production",
    model_registry_name: str = "california_housing_stacking",
    tracking_uri: str = "sqlite:///mlflow.db",
    auto_promote_to_production: bool = True,
):
    """
    Huấn luyện pipeline Stacking, theo dõi với MLflow và đăng ký vào Model Registry.
    """
    if not MLFLOW_AVAILABLE:
        print("[MLflow] Thư viện MLflow chưa được cài đặt. Vui lòng chạy: pip install mlflow")
        return None

    # Thiết lập URI theo dõi của MLflow
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    print(f"[MLflow] Đang khởi tạo lượt chạy thí nghiệm trong: {experiment_name}")

    X_train, y_train_log, X_test, y_test = load_train_test_data(log_target=True)

    with mlflow.start_run(run_name=f"stacking_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}") as run:
        run_id = run.info.run_id
        print(f"[MLflow] Run ID: {run_id}")

        # 1. Log các siêu tham số
        params = {
            "model_type": "StackingRegressor",
            "base_models": "SVR(C=30, eps=0.1) + RandomForest(n_est=300, max_depth=28)",
            "meta_model": "Ridge(alpha=1.0)",
            "cv_folds": 3,
            "random_seed": RANDOM_SEED,
            "test_size": TEST_SIZE,
            "target_transform": "log(median_house_value)",
            "n_features": len(RAW_FEATURE_COLS),
        }
        mlflow.log_params(params)

        # 2. Xây dựng và khớp mô hình
        print("[MLflow] Đang huấn luyện Stacking Regressor Pipeline...")
        pipeline = build_stacking_pipeline()
        
        start_time = time.time()
        pipeline.fit(X_train, y_train_log)
        train_duration = time.time() - start_time
        mlflow.log_metric("training_duration_seconds", round(train_duration, 2))

        # 3. Đánh giá trên tập kiểm thử
        pred_log = pipeline.predict(X_test)
        pred_values = np.exp(pred_log)
        metrics = calculate_metrics(y_test, pred_values)

        print_evaluation_report(metrics, model_name="Stacking Regressor (MLflow Run)")
        mlflow.log_metrics(metrics)

        # 4. Tạo Model Signature (Ràng buộc schema)
        sample_input = X_test.head(5)
        sample_output = np.exp(pipeline.predict(sample_input))
        signature = infer_signature(sample_input, sample_output)

        # 5. Lưu mô hình kèm Signature với format cloudpickle để tương thích với custom classes
        print("[MLflow] Đang lưu trữ artifact mô hình vào MLflow Registry...")
        try:
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                artifact_path="model",
                signature=signature,
                input_example=sample_input,
                registered_model_name=model_registry_name,
                serialization_format="cloudpickle",
            )
        except Exception:
            # Fallback nếu phiên bản dùng skops_trusted_types
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                artifact_path="model",
                signature=signature,
                input_example=sample_input,
                registered_model_name=model_registry_name,
                skops_trusted_types=[
                    "numpy.dtype",
                    "sklearn.utils._bunch.Bunch",
                    "src.data.build_features.FeatureEngineering",
                ],
            )

        # 6. Quản lý trạng thái phiên bản trong Model Registry
        client = MlflowClient()
        filter_str = f"name='{model_registry_name}'"
        registered_models = client.search_model_versions(filter_str)
        if registered_models:
            latest_version = max([int(m.version) for m in registered_models])
            print(f"[MLflow Registry] Đã đăng ký phiên bản mới thành công: v{latest_version}")

            if auto_promote_to_production:
                try:
                    client.set_registered_model_alias(
                        name=model_registry_name,
                        alias="champion",
                        version=str(latest_version),
                    )
                    print(f"[MLflow Registry] Đã gán nhãn alias 'champion' cho phiên bản v{latest_version}")
                except Exception:
                    try:
                        client.transition_model_version_stage(
                            name=model_registry_name,
                            version=str(latest_version),
                            stage="Production",
                            archive_existing_versions=True,
                        )
                        print(f"[MLflow Registry] Đã chuyển v{latest_version} sang giai đoạn Production")
                    except Exception as stage_err:
                        print(f"[MLflow Registry] Thông báo quản lý stage: {stage_err}")

        print(f"[MLflow] Quá trình hoàn tất! Khởi chạy giao diện xem bằng lệnh: mlflow ui --backend-store-uri {tracking_uri}")
        return run_id


if __name__ == "__main__":
    train_and_register_with_mlflow()
