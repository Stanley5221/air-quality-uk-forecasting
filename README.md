# Air Quality Risk Forecasting for UK Cities

> An Explainable, Reproducible Machine Learning Pipeline with a Public Health Dashboard

**Author:** Stanley Amankonah Agyei
**Institution:** University of Sunderland — MSc Data Science
**Supervisor:** Yongqiang Cheng
**Submitted:** September 2026

---

## Overview

This project builds an end-to-end pipeline that:

1. Collects hourly PM2.5, NO2, and O3 data from the UK DEFRA AURN network (2023-2024)
2. Merges pollution data with Open-Meteo historical weather
3. Engineers lag, rolling, and time features for a 24-hour-ahead PM2.5 forecast
4. Trains and compares three models: Random Forest, XGBoost, and LSTM
5. Explains model predictions with SHAP values
6. Serves live forecasts and risk maps via a Streamlit dashboard

---

## Results

| Model | RMSE (ug/m3) | MAE (ug/m3) | DAQI Accuracy |
|---|---|---|---|
| Random Forest | 5.25 | 3.92 | 79.0% |
| **XGBoost** | **5.14** | **3.78** | **80.2%** |
| LSTM | 6.41 | 4.41 | 77.5% |

**XGBoost** was selected as the primary dashboard model.
Top SHAP features: `pm25` (current), `pm25_roll_24h`, `surface_pressure`, `wind_direction_10m`.

Note on class imbalance: the 80.2% DAQI accuracy is dominated by the "Low" band (79.6% of
test hours). Macro-F1 is 0.31 and balanced accuracy is 0.31 — High-band recall is only 0.01
and Very-High-band recall is 0.00 (n=3 in the test set). See `models/daqi_confusion_matrix.png`.

---

## Repository Structure

```
air-quality-uk-forecasting/
├── data/
│   ├── raw/
│   │   └── aurn_raw_2023_2024.csv       # DEFRA AURN export (5 cities, 2 years)
│   └── processed/
│       ├── aurn_cleaned.csv             # Cleaned pollution data (87,725 rows)
│       ├── weather_historical.csv       # Open-Meteo hourly weather (87,720 rows)
│       ├── features_engineered.csv      # Merged + feature-engineered (81,028 rows)
│       └── live_readings.csv            # Latest OpenAQ readings
├── notebooks/
│   ├── 01b_fetch_weather.py             # Fetch historical weather from Open-Meteo
│   ├── 02_clean_aurn.ipynb              # AURN cleaning pipeline
│   ├── 03_feature_engineering.ipynb     # Feature engineering
│   ├── 04_random_forest.ipynb           # Random Forest training + evaluation
│   ├── 05_xgboost.ipynb                 # XGBoost training + evaluation
│   ├── 06_lstm.ipynb                    # LSTM training + evaluation
│   ├── 07_model_comparison.ipynb        # Side-by-side comparison
│   └── 08_shap_analysis.ipynb           # SHAP explainability
├── models/
│   ├── random_forest.pkl
│   ├── xgboost.json                     # Primary model
│   ├── lstm.keras + lstm_scalers.pkl
│   └── *.png                            # Charts (SHAP, comparison, forecast)
├── dashboard/
│   ├── get_live_readings.py             # Standalone OpenAQ fetch script
│   ├── live_data.py                     # Live data + model inference for dashboard
│   └── app.py                           # Streamlit app
├── tests/
│   └── test_log.csv                     # 23 functional test cases
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline (first time)

```bash
# Fetch historical weather
python notebooks/01b_fetch_weather.py

# Clean and prepare data
jupyter nbconvert --to notebook --execute --inplace notebooks/02_clean_aurn.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/03_feature_engineering.ipynb

# Train models (use higher timeout for model notebooks)
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 --inplace notebooks/04_random_forest.ipynb
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 --inplace notebooks/05_xgboost.ipynb
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1800 --inplace notebooks/06_lstm.ipynb

# Analysis
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 --inplace notebooks/07_model_comparison.ipynb
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 --inplace notebooks/08_shap_analysis.ipynb
```

### 3. Launch the dashboard

```bash
# Windows
set OPENAQ_API_KEY=<your_free_key>
streamlit run dashboard/app.py
```

Get a free OpenAQ API key at https://explore.openaq.org/register

---

## Data Sources

| Source | URL | Licence |
|---|---|---|
| DEFRA AURN | uk-air.defra.gov.uk | Open Government Licence v3 |
| Open-Meteo | open-meteo.com | CC BY 4.0 (non-commercial) |
| OpenAQ | openaq.org | CC BY 4.0 |

---

## Cities Covered

London, Birmingham, Manchester, Leeds, Edinburgh

---

## Reproducibility

See the Quick Start commands above to reproduce the full pipeline from raw data to a
running dashboard. All models use `random_state=42`. The pipeline is reproducible on any
machine with Python 3.11 and the listed dependencies; known limitations (single-season
test holdout, DAQI class imbalance) are discussed in the notebooks and test log.

---

## Dissertation Objectives Met

| # | Objective | Status |
|---|---|---|
| 1 | Literature review and project planning | Done |
| 2 | Data collection (AURN, OpenAQ, Open-Meteo) | Done |
| 3 | Data cleaning and feature engineering | Done |
| 4 | Model training (RF, XGBoost, LSTM) | Done |
| 5 | Model evaluation (RMSE, MAE, DAQI classification) | Done |
| 6 | SHAP explainability analysis | Done |
| 7 | Public-health Streamlit dashboard | Done (tested locally; public cloud URL pending) |
| 8 | Reproducibility and open-source release | Done — public repo at github.com/Stanley5221/air-quality-uk-forecasting |
