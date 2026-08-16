"""
Định nghĩa kiến trúc mô hình Stacking Regressor:
Xây dựng pipeline hồi quy kết hợp Support Vector Regression (SVR) và Random Forest Regressor
dưới dạng các mô hình cơ sở (base models) cùng mô hình tổng hợp Ridge regression (meta-estimator).
Hỗ trợ cấu hình động 100% từ file YAML.
"""
from typing import Dict, Any, Optional
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.svm import SVR

from src.config import RANDOM_SEED, N_GEO_CLUSTERS
from src.data.build_features import FeatureEngineering, build_preprocessor


def build_stacking_pipeline(
    config: Optional[Dict[str, Any]] = None,
    svr_params: Optional[Dict[str, Any]] = None,
    rf_params: Optional[Dict[str, Any]] = None,
    ridge_params: Optional[Dict[str, Any]] = None,
    cv: int = 3,
    n_jobs: int = -1,
    random_state: int = RANDOM_SEED,
) -> Pipeline:
    """
    Khởi tạo Pipeline Stacking Regressor phục vụ môi trường Production.
    Nhận tham số cấu hình linh hoạt từ dictionary (YAML) hoặc các tham số truyền trực tiếp.
    """
    cfg = config or {}
    
    # 1. Tham số Feature Engineering
    fe_cfg = cfg.get("feature_engineering", {})
    use_geo = fe_cfg.get("use_geo_cluster", True)
    n_clusters = fe_cfg.get("n_geo_clusters", N_GEO_CLUSTERS)
    seed = fe_cfg.get("random_state", random_state)

    # 2. Tham số mặc định cho các mô hình cơ sở
    svr_defaults = {"C": 30.0, "epsilon": 0.1, "gamma": "scale"}
    rf_defaults = {
        "n_estimators": 300,
        "max_depth": 28,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "random_state": seed,
        "n_jobs": n_jobs,
    }
    ridge_defaults = {"alpha": 1.0, "random_state": seed}

    # Hợp nhất cấu hình từ file YAML nếu có
    base_cfg = cfg.get("base_models", {})
    if "svr" in base_cfg:
        svr_defaults.update(base_cfg["svr"])
    if "random_forest" in base_cfg:
        rf_defaults.update(base_cfg["random_forest"])
    
    meta_cfg = cfg.get("meta_model", {})
    if "ridge" in meta_cfg:
        ridge_defaults.update(meta_cfg["ridge"])

    # Hợp nhất các tham số truyền trực tiếp (override)
    if svr_params:
        svr_defaults.update(svr_params)
    if rf_params:
        rf_defaults.update(rf_params)
    if ridge_params:
        ridge_defaults.update(ridge_params)

    # Cấu hình ensemble Stacking
    stacking_cfg = cfg.get("stacking", {})
    cv_folds = stacking_cfg.get("cv", cv)
    parallel_jobs = stacking_cfg.get("n_jobs", n_jobs)

    base_svr = SVR(**svr_defaults)
    base_rf = RandomForestRegressor(**rf_defaults)

    stacking_reg = StackingRegressor(
        estimators=[
            ("svr", base_svr),
            ("rf", base_rf),
        ],
        final_estimator=Ridge(**ridge_defaults),
        cv=cv_folds,
        n_jobs=parallel_jobs,
    )

    pipeline = Pipeline([
        ("feat_eng", FeatureEngineering(use_geo_cluster=use_geo, n_geo_clusters=n_clusters, random_state=seed)),
        ("preprocess", build_preprocessor()),
        ("model", stacking_reg),
    ])

    return pipeline
