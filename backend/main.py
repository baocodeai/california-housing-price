from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from fastapi.responses import HTMLResponse
import pandas as pd
import numpy as np
import joblib
import sqlite3
import os
from datetime import datetime
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans

class FeatureEngineering(BaseEstimator, TransformerMixin):
    def __init__(self, use_geo_cluster=True, n_geo_clusters=10,
                 cap_price=True, cap_age=True):
        self.use_geo_cluster = use_geo_cluster
        self.n_geo_clusters = n_geo_clusters
        self.cap_price = cap_price
        self.cap_age = cap_age
        self.geo_clusterer_ = None

    def fit(self, X, y=None):
        df = X.copy()

        if self.use_geo_cluster:
            coords = df[["longitude", "latitude"]].values
            self.geo_clusterer_ = KMeans(
                n_clusters=self.n_geo_clusters,
                random_state=42,
                n_init=10
            )
            self.geo_clusterer_.fit(coords)

        return self

    def transform(self, X):
        df = X.copy()

        df["ocean_proximity"] = df["ocean_proximity"].replace("ISLAND", "NEAR OCEAN")

        df["rooms_per_household"] = df["total_rooms"] / df["households"].replace(0, 1)
        df["population_per_household"] = df["population"] / df["households"].replace(0, 1)
        df["bedrooms_per_room"] = df["total_bedrooms"] / df["total_rooms"].replace(0, 1)

        if self.use_geo_cluster and self.geo_clusterer_ is not None:
            coords = df[["longitude", "latitude"]].values
            df["geo_cluster"] = self.geo_clusterer_.predict(coords)

        return df

app = FastAPI(title="California Housing Production API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the model
try:
    # Inject FeatureEngineering into __main__ so joblib can find it
    import __main__
    __main__.FeatureEngineering = FeatureEngineering

    # Model path relative to root
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'stacking_pipeline.joblib')
    loaded_rf = joblib.load(model_path)
except Exception as e:
    print(f"Failed to load model: {e}")
    loaded_rf = None

# DB Setup
DB_PATH = os.path.join(os.path.dirname(__file__), 'history.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            longitude REAL,
            latitude REAL,
            housing_median_age REAL,
            total_rooms REAL,
            total_bedrooms REAL,
            population REAL,
            households REAL,
            median_income REAL,
            ocean_proximity TEXT,
            predicted_price REAL,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class HouseFeatures(BaseModel):
    longitude: float = Field(..., ge=-125.0, le=-114.0)
    latitude: float = Field(..., ge=32.0, le=42.0)
    housing_median_age: float = Field(..., ge=1.0, le=100.0)
    total_rooms: float = Field(..., ge=1.0, le=50000.0)
    total_bedrooms: float = Field(..., ge=1.0, le=20000.0)
    population: float = Field(..., ge=1.0, le=50000.0)
    households: float = Field(..., ge=1.0, le=20000.0)
    median_income: float = Field(..., ge=0.0, le=25.0)
    ocean_proximity: Literal["<1H OCEAN", "INLAND", "NEAR OCEAN", "NEAR BAY", "ISLAND"]

@app.get("/")
def read_root():
    return {"status": "Terminal Active", "model_loaded": loaded_rf is not None}

@app.post("/predict")
def predict_price(features: HouseFeatures):
    if loaded_rf is None:
        raise HTTPException(status_code=500, detail="Model file not loaded.")
        
    # Formatting for prediction
    df = pd.DataFrame([features.dict()])
    
    try:
        pred = loaded_rf.predict(df)
        predicted_price = np.exp(pred[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # Save to db
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO predictions 
            (longitude, latitude, housing_median_age, total_rooms, total_bedrooms, population, households, median_income, ocean_proximity, predicted_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            features.longitude, features.latitude, features.housing_median_age, features.total_rooms,
            features.total_bedrooms, features.population, features.households, features.median_income,
            features.ocean_proximity, predicted_price, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving to DB: {e}")
        
    return {"status": "success", "predicted_price": float(predicted_price)}

@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM predictions ORDER BY id DESC LIMIT 50')
    rows = c.fetchall()
    conn.close()
    return {"history": [dict(ix) for ix in rows]}

@app.get("/metrics")
def get_metrics():
    # Read model_comparison.csv
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'model_comparison.csv')
    if not os.path.exists(csv_path):
        return {"error": "model_comparison.csv not found"}
    
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")

@app.get("/scatter-data")
def get_scatter_data():
    if loaded_rf is None:
        raise HTTPException(status_code=500, detail="Model file not loaded.")
        
    # Reads a subset of data to test
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'housing.csv')
    if not os.path.exists(data_path):
        return {"error": "data/housing.csv not found"}
        
    df = pd.read_csv(data_path)
    # Lọc bỏ các căn nhà bị giới hạn trần (Age = 52, Price = 500001) trong bộ nhớ 
    df = df[(df['housing_median_age'] < 52) & (df['median_house_value'] < 500000)]
    
    # Take a random sample of 100 rows
    df_sample = df.dropna().sample(n=100).copy()
    
    actual_values = df_sample['median_house_value'].values
    # Predict needs these columns (ocean_proximity needs to be passed too)
    X = df_sample[['longitude', 'latitude', 'housing_median_age', 'total_rooms', 'total_bedrooms', 'population', 'households', 'median_income', 'ocean_proximity']]
    
    preds_log = loaded_rf.predict(X)
    preds = np.exp(preds_log)
    
    result = []
    for a, p in zip(actual_values, preds):
        result.append({"actual": float(a), "predicted": float(p)})
        
    return result

@app.get("/drift-report", response_class=HTMLResponse)
def get_drift_report():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'housing.csv')
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail="Data not found")
        
    ref_df = pd.read_csv(data_path).dropna()
    
    conn = sqlite3.connect(DB_PATH)
    curr_df = pd.read_sql_query('SELECT * FROM predictions', conn)
    conn.close()
    
    if len(curr_df) == 0:
        return "<h2>Not enough data in history. Please make some predictions first.</h2>"
        
    try:
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset
        
        features = ['longitude', 'latitude', 'housing_median_age', 'total_rooms', 
                    'total_bedrooms', 'population', 'households', 'median_income', 'ocean_proximity']
        curr_data = curr_df[features].copy()
        ref_data = ref_df[features].copy()
        
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref_data, current_data=curr_data)
        return HTMLResponse(content=report.get_html(), status_code=200)
        
    except Exception as e:
        # Fallback due to user running Python 3.13 where evidently crashes (TypeError: multiple bases layout)
        from scipy.stats import ks_2samp
        features_num = ['longitude', 'latitude', 'housing_median_age', 'total_rooms', 
                    'total_bedrooms', 'population', 'households', 'median_income']
                    
        curr_data = curr_df[features_num].astype(float)
        ref_data = ref_df[features_num].astype(float)
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0c10; color: #c5c6c7; padding: 40px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #45a29e; padding: 12px; text-align: left; }}
                th {{ background: #1f2833; color: #66fcf1; text-transform: uppercase; }}
                .drift-yes {{ color: #f28b82; font-weight: bold; }}
                .drift-no {{ color: #81c995; }}
                h1 {{ color: #66fcf1; border-bottom: 2px solid #45a29e; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>Data Drift Report (Fallback Mode)</h1>
            <p><strong>Note:</strong> EvidentlyAI failed to load (Known compatibility issue with Python 3.13: <code>{str(e)}</code>). Running KS-Test Data Drift detection instead.</p>
            <table>
                <tr><th>Feature</th><th>Reference Mean</th><th>Current Mean</th><th>P-Value (KS Test)</th><th>Drift Detected (< 0.05)</th></tr>
        """
        
        drift_count = 0
        for f in features_num:
            stat, p_val = ks_2samp(ref_data[f], curr_data[f])
            is_drift = p_val < 0.05
            if is_drift: drift_count += 1
            html += f"""
            <tr>
                <td>{f}</td>
                <td>{ref_data[f].mean():.4f}</td>
                <td>{curr_data[f].mean():.4f}</td>
                <td>{p_val:.4f}</td>
                <td class="{'drift-yes' if is_drift else 'drift-no'}">{'YES' if is_drift else 'NO'}</td>
            </tr>
            """
            
        html += f"""
            </table>
            <h2 style="color: {'#f28b82' if drift_count > 0 else '#81c995'}">Overall Dataset Drift: {"DETECTED" if drift_count > 0 else "NOT DETECTED"}</h2>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=200)

