# 🏘️ California Housing Price Prediction (End-to-End MLOps)

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688)
![React](https://img.shields.io/badge/Frontend-React_Vite-61DAFB)

An end-to-end Machine Learning web application designed to predict housing prices in California. This project spans the entire lifecycle: from Exploratory Data Analysis (EDA) and Model Training (Stacking Ensembles) to API Deployment and a sleek, fully-interactive Frontend interface.

## 🌟 Key Features

### 1. Robust Machine Learning Pipeline
- Advanced **Feature Engineering**: Applied geospatial clustering (K-Means) for coordinates, ratio extraction, and clipping for artificial ceiling caps.
- **Stacking Regressor Ensemble**: Built a powerful stacking model combining Random Forest, XGBoost, Support Vector Regressors (SVR), and Ridge Regression, achieving high R² scores and low RMSE.

### 2. MLOps & System Architecture
- **FastAPI Backend**: Asynchronous and lightweight API for instant inference.
- **Strict Data Validation**: Implemented `Pydantic` layers to securely block out-of-bounds features and prevent model hallucinations.
- **Data Drift Detection**: Integrated `EvidentlyAI` with custom fallback KS-Test logic to monitor input feature distributions over time directly through the `/drift-report` endpoint.
- **Historical Ledger**: Automated local SQLite database logging for every prediction.

### 3. Brutalist Interactive Frontend
- **React + Vite**: A lightning-fast, brutalist-themed dark mode UI.
- **Interactive Geospatial Map**: Utilized `react-leaflet` combined with actual California GeoJSON boundaries. Users can seamlessly drop pins within the state to capture real-time geographical prediction coordinates.
- **Dynamic Dashboards**: Real-time *Actual vs Predicted* scatter plots (populated via dynamic SQL queries) and toggleable performance metrics.

---

## 📂 Project Structure

```text
├── backend/
│   ├── main.py                # FastAPI Application & Endpoints
│   ├── history.db             # SQLite Ledger for tracking predictions
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/                   # React Components (App.jsx, App.css)
│   └── package.json           # Frontend dependencies 
├── models/
│   └── stacking_pipeline.joblib # Serialized Production ML Pipeline
├── data/
│   └── housing.csv            # Original California Housing Dataset
├── images/                    # EDA and Evaluation plots
└── california_housing_price.ipynb # Complete Research Notebook
```

## 🚀 Getting Started

### Backend Setup (Machine Learning API)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI server (Runs on port 8000):
   ```bash
   uvicorn main:app --reload
   ```
   *Note: Access the Data Drift monitor at `http://localhost:8000/drift-report`*

### Frontend Setup (React UI)
1. Open a new terminal and navigate to the frontend:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

## 📊 Analytics Highlights

Extensive EDA mapping feature correlations, geospatial heatmaps, and target density optimizations are located inside the root `Images` folder and documented via the Jupyter Notebook.

## 🤝 Disclaimer
Data features artificial limits originally established during the 1990 California census collection.

*Engineered with precision.*
