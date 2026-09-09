import json
import os
import tarfile
import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if __name__ == "__main__":
    model_tar_path = "/opt/ml/processing/model/model.tar.gz"
    extract_path = "/opt/ml/processing/model_extracted"
    os.makedirs(extract_path, exist_ok=True)

    print(f"Extracting model artifact from {model_tar_path}...")
    with tarfile.open(model_tar_path, "r:gz") as tar:
        tar.extractall(path=extract_path)

    model_file = os.path.join(extract_path, "model.joblib")
    print(f"Loading model from {model_file}...")
    model = joblib.load(model_file)

    test_dir = "/opt/ml/processing/test"
    print(f"Loading test data from {test_dir}...")
    X_test = np.load(os.path.join(test_dir, "test_X.npy"))
    y_test = np.load(os.path.join(test_dir, "test_y.npy"))

    print("Running predictions on test set...")
    predictions = model.predict(X_test)

    r2 = float(r2_score(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    mae = float(mean_absolute_error(y_test, predictions))

    print(f"Evaluation Metrics: R2 Score = {r2:.4f}, RMSE = {rmse:.4f}, MAE = {mae:.4f}")

    report_dict = {
        "regression_metrics": {
            "r2_score": {
                "value": r2
            },
            "rmse": {
                "value": rmse
            },
            "mae": {
                "value": mae
            }
        }
    }

    eval_dir = "/opt/ml/processing/evaluation"
    os.makedirs(eval_dir, exist_ok=True)
    eval_file = os.path.join(eval_dir, "evaluation.json")

    with open(eval_file, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"Saved evaluation report to {eval_file}")
