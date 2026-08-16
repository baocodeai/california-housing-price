"""
Kịch bản tinh chỉnh siêu tham số (Hyperparameter Tuning) cho Stacking Regressor:
Tự động hóa theo cấu hình YAML sử dụng RandomizedSearchCV.
Đọc không gian tham số và thiết lập tối ưu trực tiếp từ configs/stacking.yaml.
"""
import argparse
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline

from src.data.dataloader import load_train_test_data
from src.models.stacking.model import build_stacking_pipeline


def tune_hyperparameters(
    config_path: Optional[str] = "configs/stacking.yaml",
    n_iter: Optional[int] = None,
    cv: Optional[int] = None,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Thực thi tối ưu siêu tham số dựa trên thiết lập trong file cấu hình YAML.
    """
    cfg: Dict[str, Any] = {}
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print(f"[Tuning] Đã nạp cấu hình tinh chỉnh từ {config_path}")

    tuning_cfg = cfg.get("tuning", {})
    search_n_iter = n_iter or tuning_cfg.get("n_iter", 10)
    search_cv = cv or tuning_cfg.get("cv", 3)
    scoring = tuning_cfg.get("scoring", "neg_root_mean_squared_error")
    seed = tuning_cfg.get("random_state", 42)

    # Không gian tìm kiếm tham số từ YAML hoặc mặc định
    param_distributions = tuning_cfg.get("param_distributions", {
        "model__svr__C": [10.0, 20.0, 30.0, 50.0],
        "model__svr__epsilon": [0.05, 0.1, 0.2],
        "model__rf__n_estimators": [100, 200, 300],
        "model__rf__max_depth": [20, 28, 35, None],
        "model__final_estimator__alpha": [0.1, 1.0, 10.0],
    })

    print(f"[Tuning] Đang nạp dữ liệu tìm kiếm siêu tham số (n_iter={search_n_iter}, cv={search_cv})...")
    X_train, y_train_log, _, _ = load_train_test_data(log_target=True)

    base_pipeline = build_stacking_pipeline(config=cfg)

    search = RandomizedSearchCV(
        base_pipeline,
        param_distributions=param_distributions,
        n_iter=search_n_iter,
        cv=search_cv,
        scoring=scoring,
        random_state=seed,
        n_jobs=-1,
        verbose=1,
    )

    print("[Tuning] Bắt đầu quá trình RandomizedSearchCV...")
    search.fit(X_train, y_train_log)

    print("==========================================")
    print(f" Điểm CV tốt nhất ({scoring}): {search.best_score_:.4f}")
    print(f" Bộ siêu tham số tốt nhất: {search.best_params_}")
    print("==========================================")

    return search.best_estimator_, search.best_params_


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tinh chỉnh siêu tham số mô hình Stacking")
    parser.add_argument("-c", "--config", type=str, default="configs/stacking.yaml", help="Đường dẫn file cấu hình YAML")
    parser.add_argument("--n-iter", type=int, default=None, help="Số lượng mẫu tham số thử nghiệm")
    parser.add_argument("--cv", type=int, default=None, help="Số fold cross-validation")
    args = parser.parse_args()

    tune_hyperparameters(config_path=args.config, n_iter=args.n_iter, cv=args.cv)
