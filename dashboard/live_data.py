
import os, pathlib, datetime, warnings
import pytz
import requests
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "dashboard" / ".env")
load_dotenv()


CITIES = [
    {"station": "London Marylebone Road",    "short": "London",     "lat": 51.51, "lon": -0.13},
    {"station": "Birmingham A4540 Roadside", "short": "Birmingham", "lat": 52.48, "lon": -1.90},
    {"station": "Manchester Piccadilly",     "short": "Manchester", "lat": 53.48, "lon": -2.24},
    {"station": "Leeds Centre",              "short": "Leeds",      "lat": 53.80, "lon": -1.55},
    {"station": "Edinburgh St Leonards",     "short": "Edinburgh",  "lat": 55.95, "lon": -3.19},
]

FEATURE_COLS = [
    "o3", "no2", "pm25",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_10m", "precipitation", "surface_pressure",
    "hour", "day_of_week", "month", "is_weekend",
    "pm25_lag_1", "pm25_lag_2", "pm25_lag_3", "pm25_lag_24",
    "pm25_roll_24h", "pm25_roll_72h",
]

DAQI_BANDS = [
    (12,  "Low",       "#9CFF9C"),
    (24,  "Moderate",  "#FFFF00"),
    (48,  "High",      "#FF7F00"),
    (999, "Very High", "#FF0000"),
]

OPENAQ_BASE        = "https://api.openaq.org/v3"
METEO_BASE         = "https://api.open-meteo.com/v1/forecast"
METEO_ARCHIVE_BASE = "https://archive-api.open-meteo.com/v1/archive"


# ---------------------------------------------------------------------------
# DAQI helpers
# ---------------------------------------------------------------------------

def daqi_band(pm25: float) -> tuple[str, str]:
    """Return (band_name, hex_colour) for a PM2.5 concentration."""
    for threshold, name, colour in DAQI_BANDS:
        if pm25 < threshold:
            return name, colour
    return "Very High", "#FF0000"


# ---------------------------------------------------------------------------
# OpenAQ live PM2.5
# ---------------------------------------------------------------------------

def _openaq_session() -> requests.Session:
    s = requests.Session()
    key = os.environ.get("OPENAQ_API_KEY", "")
    if key:
        s.headers["X-API-Key"] = key
    return s


def _fetch_live_pm25_full(session: requests.Session, lat: float, lon: float) -> dict:
    """
    Return a dict with live PM2.5 data from the nearest active OpenAQ station:
        value            (float)  — PM2.5 concentration in µg/m³
        station_name     (str)    — human-readable station name
        reading_timestamp(str)    — ISO UTC datetime of the sensor reading
    Returns an empty dict on failure.
    """
    try:
        r = session.get(
            f"{OPENAQ_BASE}/locations",
            params={"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 10},
            timeout=10,
        )
        r.raise_for_status()
        best_reading = None
        for loc in r.json().get("results", []):
            pm25_sensors = {
                s["id"]: s for s in loc.get("sensors", [])
                if s.get("parameter", {}).get("name", "").lower() == "pm25"
            }
            if not pm25_sensors:
                continue
            loc_id = loc["id"]
            station_name = loc.get("name", "Unknown Station")
            try:
                r2 = session.get(f"{OPENAQ_BASE}/locations/{loc_id}/latest", timeout=8)
                if r2.status_code != 200:
                    continue
                for m in r2.json().get("results", []):
                    sid = m.get("sensorsId")
                    val = m.get("value")
                    # val > 0 rather than >= 0: a literal 0.0 is essentially never a genuine
                    # ambient PM2.5 reading and is a common fault/offline signature from
                    # low-cost community sensors on OpenAQ; treat it as no reading rather than
                    # letting a dead sensor's "most recent timestamp" beat a real, slightly
                    # older reading from a reference-grade station.
                    if sid in pm25_sensors and val is not None and val > 0:
                        ts = m.get("datetime", {})
                        reading_timestamp = ts.get("utc", "") if isinstance(ts, dict) else str(ts)
                        if not best_reading or reading_timestamp > best_reading["reading_timestamp"]:
                            best_reading = {
                                "value": float(val),
                                "station_name": station_name,
                                "reading_timestamp": reading_timestamp,
                                "data_source": "OpenAQ (Live Sensor)",
                            }
            except Exception:
                continue
        if best_reading:
            return best_reading
    except Exception:
        pass
    return {}


def _fetch_openmeteo_air_quality(lat: float, lon: float) -> dict:
    """Fallback to Open-Meteo free live air quality API if OpenAQ is unavailable."""
    try:
        r = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "pm2_5",
                "timezone": "UTC",
            },
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json().get("current", {})
            val = data.get("pm2_5")
            time_str = data.get("time", "")
            if val is not None and val > 0:
                return {
                    "value": float(val),
                    "station_name": "Open-Meteo / Copernicus Model",
                    "reading_timestamp": time_str + ":00Z" if time_str else "",
                    "data_source": "Open-Meteo (Live Model)",
                }
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Open-Meteo current weather
# ---------------------------------------------------------------------------

def _fetch_current_weather(lat: float, lon: float) -> dict:
    """Return current weather dict from Open-Meteo forecast endpoint."""
    try:
        r = requests.get(
            METEO_BASE,
            params={
                "latitude":  lat,
                "longitude": lon,
                "current":   (
                    "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                    "wind_direction_10m,precipitation,surface_pressure"
                ),
                "timezone": "UTC",
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("current", {})
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Detailed weather forecast (hourly + daily) for rich weather widget
# ---------------------------------------------------------------------------

def get_weather_forecast_detailed(lat: float, lon: float) -> dict:
    """
    Fetch 48h hourly + 7-day daily weather from Open-Meteo.
    Returns dict with keys 'hourly' and 'daily'.
    """
    try:
        r = requests.get(
            METEO_BASE,
            params={
                "latitude":  lat,
                "longitude": lon,
                "hourly": (
                    "temperature_2m,precipitation_probability,precipitation,"
                    "wind_speed_10m,wind_direction_10m,relative_humidity_2m,weather_code"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,wind_speed_10m_max"
                ),
                "current": (
                    "temperature_2m,weather_code,wind_speed_10m,"
                    "relative_humidity_2m,precipitation,surface_pressure"
                ),
                "timezone": "Europe/London",
                "forecast_days": 8,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "hourly":  data.get("hourly", {}),
            "daily":   data.get("daily", {}),
            "current": data.get("current", {}),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Historical AURN tail for lag / rolling features
# ---------------------------------------------------------------------------

def _load_aurn_tail(station: str, n: int = 72) -> pd.DataFrame:
    """Load last n hourly rows for a station from the cleaned AURN CSV."""
    path = ROOT / "data" / "processed" / "aurn_cleaned.csv"
    df   = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    city_df = df[df["city"] == station].sort_index()
    return city_df.tail(n)


# ---------------------------------------------------------------------------
# Feature vector assembly
# ---------------------------------------------------------------------------

def _build_feature_row(
    city_info: dict,
    pm25_live: float,
    weather: dict,
    aurn_tail: pd.DataFrame,
    now: datetime.datetime,
) -> dict:
    """Assemble one row of features matching FEATURE_COLS."""

    # Time features
    hour       = now.hour
    dow        = now.weekday()
    month      = now.month
    is_weekend = int(dow >= 5)

    # Pollution: use live PM2.5; take o3/no2 from last AURN row
    last = aurn_tail.iloc[-1] if len(aurn_tail) else None
    o3   = float(last["o3"])  if last is not None and pd.notna(last["o3"])  else 0.0
    no2  = float(last["no2"]) if last is not None and pd.notna(last["no2"]) else 0.0

    # Lag features from AURN tail (drop NaN before indexing)
    pm25_series = aurn_tail["pm25"].dropna()

    def _lag(n):
        return float(pm25_series.iloc[-n]) if len(pm25_series) >= n else pm25_live

    lag1  = _lag(1)
    lag2  = _lag(2)
    lag3  = _lag(3)
    lag24 = _lag(24)
    roll24 = float(pm25_series.tail(24).mean()) if len(pm25_series) >= 1 else pm25_live
    roll72 = float(pm25_series.tail(72).mean()) if len(pm25_series) >= 1 else pm25_live

    # Weather
    def _w(key, default=0.0):
        return float(weather.get(key, default))

    return {
        "o3":                   o3,
        "no2":                  no2,
        "pm25":                 pm25_live,
        "temperature_2m":       _w("temperature_2m"),
        "relative_humidity_2m": _w("relative_humidity_2m"),
        "wind_speed_10m":       _w("wind_speed_10m"),
        "wind_direction_10m":   _w("wind_direction_10m"),
        "precipitation":        _w("precipitation"),
        "surface_pressure":     _w("surface_pressure", 1013.0),
        "hour":                 hour,
        "day_of_week":          dow,
        "month":                month,
        "is_weekend":           is_weekend,
        "pm25_lag_1":           lag1,
        "pm25_lag_2":           lag2,
        "pm25_lag_3":           lag3,
        "pm25_lag_24":          lag24,
        "pm25_roll_24h":        roll24,
        "pm25_roll_72h":        roll72,
    }


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def get_forecast() -> pd.DataFrame:
    """
    Fetch live PM2.5 + weather for all cities, run XGBoost, return a DataFrame.

    Columns:
        city_short, station, lat, lon,
        pm25_current, pm25_forecast_24h,
        daqi_current, daqi_current_colour,
        daqi_forecast, daqi_forecast_colour,
        last_updated
    """
    model = xgb.XGBRegressor()
    model.load_model(str(ROOT / "models" / "xgboost.json"))

    session = _openaq_session()
    now     = datetime.datetime.utcnow()
    rows    = []

    for city in CITIES:
        station = city["station"]

        # Live PM2.5 — try full fetch (value + station name + timestamp)
        live_result = _fetch_live_pm25_full(session, city["lat"], city["lon"])
        aurn_tail = _load_aurn_tail(station, n=72)

        is_recent_openaq = False
        if live_result and live_result.get("value", -1) >= 0:
            ts = live_result.get("reading_timestamp", "")
            if ts and any(y in ts for y in ["2026", "2025", "2024"]):
                is_recent_openaq = True

        if is_recent_openaq:
            pm25_live         = live_result["value"]
            live_station_name = live_result["station_name"]
            reading_timestamp = live_result["reading_timestamp"]
            data_source       = "OpenAQ (Live Sensor)"
        else:
            # Try Open-Meteo real-time air quality fallback
            om_result = _fetch_openmeteo_air_quality(city["lat"], city["lon"])
            if om_result and om_result.get("value", -1) >= 0:
                pm25_live         = om_result["value"]
                live_station_name = om_result["station_name"]
                reading_timestamp = om_result["reading_timestamp"]
                data_source       = "Open-Meteo (Live Model)"
            elif live_result and live_result.get("value", -1) >= 0:
                pm25_live         = live_result["value"]
                live_station_name = live_result["station_name"]
                reading_timestamp = live_result["reading_timestamp"]
                data_source       = "OpenAQ (Live Sensor)"
            else:
                # Fallback to last AURN historical value
                pm25_live         = float(aurn_tail["pm25"].dropna().iloc[-1]) if len(aurn_tail) else 5.0
                live_station_name = station + " (AURN Historical)"
                reading_timestamp = ""
                data_source       = "AURN Historical (Fallback)"

        # Current weather
        weather = _fetch_current_weather(city["lat"], city["lon"])

        # Feature vector -> model prediction (24h)
        feat_row = _build_feature_row(city, pm25_live, weather, aurn_tail, now)
        X        = np.array([[feat_row[c] for c in FEATURE_COLS]])
        pm25_fcast = float(np.clip(model.predict(X)[0], 0, None))

        # 48h Prediction (Recursive): the model maps (features at t) -> (pm25 at t+24h),
        # and pm25_fcast already represents the predicted value AT now+24h, so the
        # reference time for this second stage must be now+24h (not now+48h) — the
        # model itself projects the remaining +24h to reach now+48h.
        ref_24h = now + datetime.timedelta(hours=24)
        weather_ref24h = _fetch_weather_for_datetime(city["lat"], city["lon"], ref_24h)
        # Note: pm25_lag_2/_lag_3/roll_72h for this stage are approximated from a single
        # synthetic point at ref_24h, since no real hourly data exists for now->now+24h yet
        # (it hasn't happened) -- an inherent limitation of one-step-recursive forecasting.
        dummy_tail = aurn_tail.copy()
        if len(dummy_tail) > 0:
            dummy_tail.loc[ref_24h] = dummy_tail.iloc[-1]
            dummy_tail.iloc[-1, dummy_tail.columns.get_loc("pm25")] = pm25_fcast

        feat_row_48h = _build_feature_row(city, pm25_fcast, weather_ref24h, dummy_tail, ref_24h)
        X_48h        = np.array([[feat_row_48h[c] for c in FEATURE_COLS]])
        pm25_fcast_48h = float(np.clip(model.predict(X_48h)[0], 0, None))

        band_now,  col_now  = daqi_band(pm25_live)
        band_fore, col_fore = daqi_band(pm25_fcast)
        band_fore48, col_fore48 = daqi_band(pm25_fcast_48h)

        rows.append({
            "city_short":               city["short"],
            "station":                  station,
            "live_station_name":        live_station_name,
            "reading_timestamp":        reading_timestamp,
            "data_source":              data_source,
            "lat":                      city["lat"],
            "lon":                      city["lon"],
            "pm25_current":             round(pm25_live,  1),
            "pm25_forecast_24h":        round(pm25_fcast, 1),
            "pm25_forecast_48h":        round(pm25_fcast_48h, 1),
            "daqi_current":             band_now,
            "daqi_current_colour":      col_now,
            "daqi_forecast":            band_fore,
            "daqi_forecast_colour":     col_fore,
            "daqi_forecast_48h":        band_fore48,
            "daqi_forecast_48h_colour": col_fore48,
            "last_updated":             now.strftime("%Y-%m-%d %H:%M UTC"),
            # --- Weather sub-readings ---
            "temperature":              round(float(weather.get("temperature_2m", 0)), 1),
            "humidity":                 round(float(weather.get("relative_humidity_2m", 0)), 1),
            "wind_speed":               round(float(weather.get("wind_speed_10m", 0)), 1),
            "wind_direction":           round(float(weather.get("wind_direction_10m", 0)), 0),
            "precipitation":            round(float(weather.get("precipitation", 0)), 2),
            "pressure":                 round(float(weather.get("surface_pressure", 1013)), 1),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Advanced Features (What-If, SHAP, History)
# ---------------------------------------------------------------------------



def get_city_history(city_name: str, pm25_current: float = None, pm25_forecast_24h: float = None, month: int = None, day: int = None) -> pd.DataFrame:
    """Return same-day historical PM2.5 comparison across 2023, 2024, and current live/forecast."""
    city_info = next((c for c in CITIES if c["short"] == city_name), CITIES[0])
    station = city_info["station"]
    
    path = ROOT / "data" / "processed" / "aurn_cleaned.csv"
    df = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    city_df = df[df["city"] == station].sort_index()
    
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.datetime.now(uk_tz)
    target_m = month if month is not None else now.month
    target_d = day if day is not None else now.day
    
    sub = city_df[(city_df.index.month == target_m) & (city_df.index.day == target_d)].copy()
    
    # If no data found for exact date, fall back to last 24h of dataset
    if sub.empty:
        sub = city_df.tail(24).copy()
        
    sub["Hour"] = sub.index.strftime("%H:00")
    sub["Year"] = sub.index.year.astype(str)
    
    res_df = sub[["Hour", "pm25", "Year"]].rename(columns={"pm25": "PM2.5 (µg/m³)"})
    
    if pm25_current is not None and pm25_forecast_24h is not None:
        curr_hour_str = now.strftime("%H:00")
        fore_hour_str = (now + datetime.timedelta(hours=24)).strftime("%H:00")
        
        live_rows = pd.DataFrame([
            {"Hour": curr_hour_str, "PM2.5 (µg/m³)": pm25_current, "Year": "Current / Forecast"},
            {"Hour": fore_hour_str, "PM2.5 (µg/m³)": pm25_forecast_24h, "Year": "Current / Forecast"},
        ])
        res_df = pd.concat([res_df, live_rows], ignore_index=True)
        
    return res_df


def get_all_cities_history(month: int = None, day: int = None) -> pd.DataFrame:
    """Return daily mean PM2.5 for all cities on the same calendar day in 2023 and 2024."""
    path = ROOT / "data" / "processed" / "aurn_cleaned.csv"
    df = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    
    uk_tz = pytz.timezone("Europe/London")
    now = datetime.datetime.now(uk_tz)
    target_m = month if month is not None else now.month
    target_d = day if day is not None else now.day
    
    sub = df[(df.index.month == target_m) & (df.index.day == target_d)].copy()
    if sub.empty:
        sub = df.tail(120).copy()
        
    grouped = sub.groupby(["city", sub.index.year])["pm25"].mean().reset_index()
    grouped.columns = ["Station", "Year", "PM2.5 (µg/m³)"]
    
    station_map = {c["station"]: c["short"] for c in CITIES}
    grouped["City"] = grouped["Station"].map(station_map)
    grouped["Year"] = grouped["Year"].astype(str)
    
    return grouped[["City", "Year", "PM2.5 (µg/m³)"]].dropna()


# ---------------------------------------------------------------------------
# Custom Prediction Explorer — weather fetch + model run for any datetime
# ---------------------------------------------------------------------------

_WEATHER_HOURLY_VARS = (
    "temperature_2m,relative_humidity_2m,wind_speed_10m,"
    "wind_direction_10m,precipitation,surface_pressure"
)
_WEATHER_KEYS = [
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_10m", "precipitation", "surface_pressure",
]


def _fetch_weather_for_datetime(lat: float, lon: float, target_dt: datetime.datetime) -> dict:
    """
    Fetch weather for a specific datetime.
    Uses Open-Meteo Archive API for past dates; Forecast API for future/today.
    Falls back to plausible UK defaults on failure.
    """
    DEFAULTS = {
        "temperature_2m": 12.0, "relative_humidity_2m": 75.0,
        "wind_speed_10m": 10.0, "wind_direction_10m": 200.0,
        "precipitation": 0.0,   "surface_pressure": 1013.0,
    }
    date_str    = target_dt.strftime("%Y-%m-%d")
    target_hour = target_dt.hour
    now_utc     = datetime.datetime.utcnow()
    is_past     = target_dt.date() < now_utc.date()

    try:
        if is_past:
            r = requests.get(
                METEO_ARCHIVE_BASE,
                params={
                    "latitude": lat, "longitude": lon,
                    "start_date": date_str, "end_date": date_str,
                    "hourly": _WEATHER_HOURLY_VARS,
                    "timezone": "UTC",
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json().get("hourly", {})
            n    = len(data.get("temperature_2m", [0] * 24))
            idx  = min(target_hour, n - 1)
        else:
            delta = (target_dt.date() - now_utc.date()).days
            r = requests.get(
                METEO_BASE,
                params={
                    "latitude": lat, "longitude": lon,
                    "hourly": _WEATHER_HOURLY_VARS,
                    "timezone": "UTC",
                    "forecast_days": min(16, max(4, delta + 2)),
                },
                timeout=15,
            )
            r.raise_for_status()
            data   = r.json().get("hourly", {})
            target = target_dt.strftime("%Y-%m-%dT%H:00")
            times  = data.get("time", [])
            idx    = times.index(target) if target in times else 0

        return {k: float(data.get(k, [DEFAULTS[k]] * 200)[idx]) for k in _WEATHER_KEYS}

    except Exception:
        return DEFAULTS.copy()


def predict_custom(city_name: str, target_dt: datetime.datetime) -> dict:
    """
    Run the XGBoost model for any city and any datetime.

    The model was trained on (features at time t) -> (pm25 at t+24h)
    (see notebooks/03_feature_engineering.ipynb, pm25_next24h = shift(-24)).
    To predict PM2.5 *at* target_dt, the input feature row must therefore
    describe conditions 24 hours *before* target_dt — the model itself
    performs the +24h projection.

    Returns a dict with:
        pm25_predicted     — rounded PM2.5 µg/m³
        daqi_band          — DAQI category string
        daqi_colour        — hex colour
        weather            — weather values used (at reference_datetime)
        features           — full 19-feature dict passed to the model
        pm25_context       — recent PM2.5 baseline used for lags
        data_note          — source note string
        reference_datetime — the actual time the input features describe
        shap_top_features  — top 5 SHAP contributions for this prediction
    """
    city_info = next((c for c in CITIES if c["short"] == city_name), CITIES[0])
    station   = city_info["station"]
    ref_dt    = target_dt - datetime.timedelta(hours=24)

    # Load XGBoost model
    model = xgb.XGBRegressor()
    model.load_model(str(ROOT / "models" / "xgboost.json"))

    # Load AURN data for lags
    path    = ROOT / "data" / "processed" / "aurn_cleaned.csv"
    df_aurn = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    city_df = df_aurn[df_aurn["city"] == station].sort_index()

    # Get rows leading up to the reference datetime (target_dt - 24h)
    hist_before = city_df[city_df.index <= ref_dt]
    if len(hist_before) >= 1:
        aurn_tail = hist_before.tail(72)
        data_note = "AURN historical records"
    else:
        aurn_tail = city_df.tail(72)          # use most recent data as proxy
        data_note = "seasonal proxy (no AURN record before this date)"

    pm25_series = aurn_tail["pm25"].dropna()
    pm25_ctx    = float(pm25_series.iloc[-1]) if len(pm25_series) > 0 else 8.0

    last = aurn_tail.iloc[-1] if len(aurn_tail) > 0 else None
    o3   = float(last["o3"])  if (last is not None and pd.notna(last.get("o3")))  else 40.0
    no2  = float(last["no2"]) if (last is not None and pd.notna(last.get("no2"))) else 25.0

    def _lag(n):
        return float(pm25_series.iloc[-n]) if len(pm25_series) >= n else pm25_ctx

    lag1   = _lag(1);  lag2  = _lag(2);  lag3  = _lag(3);  lag24 = _lag(24)
    roll24 = float(pm25_series.tail(24).mean()) if len(pm25_series) >= 1 else pm25_ctx
    roll72 = float(pm25_series.tail(72).mean()) if len(pm25_series) >= 1 else pm25_ctx

    # Fetch weather for the reference datetime (target_dt - 24h), not target_dt itself
    weather = _fetch_weather_for_datetime(city_info["lat"], city_info["lon"], ref_dt)

    def _w(k, default=0.0):
        return float(weather.get(k, default))

    feat_row = {
        "o3":                   o3,
        "no2":                  no2,
        "pm25":                 pm25_ctx,
        "temperature_2m":       _w("temperature_2m"),
        "relative_humidity_2m": _w("relative_humidity_2m"),
        "wind_speed_10m":       _w("wind_speed_10m"),
        "wind_direction_10m":   _w("wind_direction_10m"),
        "precipitation":        _w("precipitation"),
        "surface_pressure":     _w("surface_pressure", 1013.0),
        "hour":                 ref_dt.hour,
        "day_of_week":          ref_dt.weekday(),
        "month":                ref_dt.month,
        "is_weekend":           int(ref_dt.weekday() >= 5),
        "pm25_lag_1":           lag1,
        "pm25_lag_2":           lag2,
        "pm25_lag_3":           lag3,
        "pm25_lag_24":          lag24,
        "pm25_roll_24h":        round(roll24, 1),
        "pm25_roll_72h":        round(roll72, 1),
    }

    X          = np.array([[feat_row[c] for c in FEATURE_COLS]])
    pm25_pred  = float(np.clip(model.predict(X)[0], 0, None))
    band, col  = daqi_band(pm25_pred)

    # Local SHAP explanation for this specific prediction
    explainer   = shap.TreeExplainer(model)
    X_df        = pd.DataFrame([feat_row])[FEATURE_COLS]
    shap_row    = explainer.shap_values(X_df)[0]
    contributions = sorted(
        zip(FEATURE_COLS, shap_row, X_df.iloc[0].values),
        key=lambda t: abs(t[1]), reverse=True,
    )[:5]
    shap_top_features = [
        {"feature": f, "shap_value": round(float(v), 3), "feature_value": round(float(x), 2)}
        for f, v, x in contributions
    ]

    return {
        "pm25_predicted": round(pm25_pred, 1),
        "daqi_band":      band,
        "daqi_colour":    col,
        "city":           city_name,
        "station":        station,
        "target_datetime":    target_dt,
        "reference_datetime": ref_dt,
        "weather":        {k: round(v, 1) for k, v in weather.items()},
        "pm25_context":   round(pm25_ctx, 1),
        "features":       feat_row,
        "data_note":      data_note,
        "shap_top_features": shap_top_features,
    }
