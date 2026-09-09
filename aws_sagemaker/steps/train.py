import argparse
import os
import shutil
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.svm import SVR

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=15)
    args = parser.parse_args()

    train_dir = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")
    print(f"Loading training data from {train_dir}...")
    X_train = np.load(os.path.join(train_dir, "train_X.npy"))
    y_train = np.load(os.path.join(train_dir, "train_y.npy"))

    print(f"Training dataset shape: X={X_train.shape}, y={y_train.shape}")
    print("Initializing Stacking Regressor (RandomForest + SVR with Ridge meta-model)...")
    base_estimators = [
        ("rf", RandomForestRegressor(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            random_state=42,
            n_jobs=-1
        )),
        ("svr", SVR(C=1.0, epsilon=0.2))
    ]

    model = StackingRegressor(
        estimators=base_estimators,
        final_estimator=RidgeCV(),
        cv=5,
        n_jobs=-1
    )

    print("Fitting model...")
    model.fit(X_train, y_train)

    # Thư mục chứa model artifact của SageMaker (sẽ tự động nén thành model.tar.gz)
    model_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
    os.makedirs(model_dir, exist_ok=True)

    model_path = os.path.join(model_dir, "model.joblib")
    joblib.dump(model, model_path)
    print(f"Saved model to {model_path}")

    # Đóng gói kèm file preprocessor.joblib nếu có để serving tự giải nén và dùng
    preprocessor_src = os.path.join(train_dir, "preprocessor.joblib")
    if os.path.exists(preprocessor_src):
        shutil.copy(preprocessor_src, os.path.join(model_dir, "preprocessor.joblib"))
        print("Copied preprocessor.joblib to model directory for self-contained serving.")

    print("Training finished successfully!")
