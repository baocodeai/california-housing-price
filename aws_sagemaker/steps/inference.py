import json
import os
import joblib
import pandas as pd

def model_fn(model_dir):
    """Được gọi một lần khi container khởi động để nạp model và preprocessor."""
    model_path = os.path.join(model_dir, "model.joblib")
    preprocessor_path = os.path.join(model_dir, "preprocessor.joblib")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")

    model = joblib.load(model_path)
    preprocessor = None
    if os.path.exists(preprocessor_path):
        preprocessor = joblib.load(preprocessor_path)

    return {"model": model, "preprocessor": preprocessor}

def input_fn(request_body, request_content_type):
    """Tiếp nhận và parse JSON payload từ API Gateway hoặc Client."""
    if request_content_type == "application/json":
        data = json.loads(request_body)
        instances = data.get("instances", [])
        if not instances:
            raise ValueError("Payload must contain 'instances' list.")

        columns = [
            "longitude", "latitude", "housing_median_age", "total_rooms",
            "total_bedrooms", "population", "households", "median_income",
            "ocean_proximity"
        ]
        df = pd.DataFrame(instances, columns=columns)

        # Tính toán các engineered features
        df["rooms_per_household"] = df["total_rooms"] / df["households"]
        df["bedrooms_per_room"] = df["total_bedrooms"] / df["total_rooms"]
        df["population_per_household"] = df["population"] / df["households"]

        return df
    raise ValueError(f"Content type '{request_content_type}' is not supported. Use 'application/json'.")

def predict_fn(input_data, artifacts):
    """Transform features và gọi StackingRegressor để dự đoán."""
    model = artifacts["model"]
    preprocessor = artifacts["preprocessor"]

    if preprocessor is not None:
        X_transformed = preprocessor.transform(input_data)
    else:
        X_transformed = input_data

    predictions = model.predict(X_transformed)
    return predictions

def output_fn(prediction, accept):
    """Format kết quả dự đoán trả về JSON."""
    return json.dumps({"predictions": prediction.tolist()}), "application/json"
