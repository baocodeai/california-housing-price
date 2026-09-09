import argparse
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-test-split-ratio", type=float, default=0.3)
    args = parser.parse_args()

    input_data_path = "/opt/ml/processing/input/housing.csv"
    if not os.path.exists(input_data_path):
        # Fallback cho testing cục bộ nếu cần
        input_data_path = os.path.join(os.getcwd(), "data/raw/housing.csv")

    print(f"Reading raw data from {input_data_path}...")
    df = pd.read_csv(input_data_path)

    # 1. Feature Engineering
    df["rooms_per_household"] = df["total_rooms"] / df["households"]
    df["bedrooms_per_room"] = df["total_bedrooms"] / df["total_rooms"]
    df["population_per_household"] = df["population"] / df["households"]

    X = df.drop(columns=["median_house_value"])
    y = df["median_house_value"]

    num_cols = [
        "longitude", "latitude", "housing_median_age", "total_rooms",
        "total_bedrooms", "population", "households", "median_income",
        "rooms_per_household", "bedrooms_per_room", "population_per_household"
    ]
    cat_cols = ["ocean_proximity"]

    # 2. Pipeline tiền xử lý
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    preprocessor = ColumnTransformer([
        ("num", num_pipeline, num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])

    print("Fitting preprocessor...")
    X_transformed = preprocessor.fit_transform(X)

    # 3. Chia tập dữ liệu (70% Train, 15% Validation, 15% Test)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_transformed, y.values, test_size=args.train_test_split_ratio, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )

    output_dir = "/opt/ml/processing/output"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Saving preprocessed data to {output_dir}...")
    np.save(os.path.join(output_dir, "train_X.npy"), X_train)
    np.save(os.path.join(output_dir, "train_y.npy"), y_train)
    np.save(os.path.join(output_dir, "val_X.npy"), X_val)
    np.save(os.path.join(output_dir, "val_y.npy"), y_val)
    np.save(os.path.join(output_dir, "test_X.npy"), X_test)
    np.save(os.path.join(output_dir, "test_y.npy"), y_test)

    # Lưu preprocessor object để phục vụ inference
    joblib.dump(preprocessor, os.path.join(output_dir, "preprocessor.joblib"))
    print("Preprocessing completed successfully!")
