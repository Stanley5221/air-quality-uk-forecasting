"""
Fetch hourly historical weather from the Open-Meteo archive API for five UK
cities over 2023-01-01 to 2024-12-31, then save to
data/processed/weather_historical.csv.

No API key required — Open-Meteo is free for non-commercial use.
"""

import pathlib
import time
import requests
import pandas as pd

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

CITIES = [
    {"name": "London",     "lat": 51.51, "lon": -0.13},
    {"name": "Birmingham", "lat": 52.48, "lon": -1.90},
    {"name": "Manchester", "lat": 53.48, "lon": -2.24},
    {"name": "Leeds",      "lat": 53.80, "lon": -1.55},
    {"name": "Edinburgh",  "lat": 55.95, "lon": -3.19},
]

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "surface_pressure",
]

START_DATE = "2023-01-01"
END_DATE   = "2024-12-31"


def fetch_city(city: dict) -> pd.DataFrame:
    params = {
        "latitude":   city["lat"],
        "longitude":  city["lon"],
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "hourly":     ",".join(HOURLY_VARS),
        "timezone":   "UTC",
    }
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()

    hourly = resp.json()["hourly"]
    df = pd.DataFrame(hourly)
    df.rename(columns={"time": "datetime"}, inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.insert(0, "city", city["name"])
    return df


def main() -> None:
    frames = []

    for city in CITIES:
        print(f"  Fetching {city['name']}...", end=" ", flush=True)
        try:
            df = fetch_city(city)
            frames.append(df)
            print(f"{len(df):,} rows")
        except requests.HTTPError as exc:
            print(f"HTTP error — {exc}")
        except Exception as exc:
            print(f"error — {exc}")
        time.sleep(0.5)  # polite pause between requests

    if not frames:
        print("No data retrieved — exiting.")
        return

    combined = pd.concat(frames, ignore_index=True)

    out_path = (
        pathlib.Path(__file__).parent.parent
        / "data" / "processed" / "weather_historical.csv"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)

    print(f"\nSaved {len(combined):,} rows × {len(combined.columns)} columns to {out_path}")
    print(combined.head(3).to_string(index=False))


if __name__ == "__main__":
    print(f"Fetching hourly weather {START_DATE} to {END_DATE} for {len(CITIES)} cities...")
    main()
