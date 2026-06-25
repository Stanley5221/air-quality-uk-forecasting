"""
Fetch the latest PM2.5 readings for UK monitoring stations near five cities
using the OpenAQ v3 API, then save results to data/processed/live_readings.csv.

Requires an OpenAQ API key set in the environment:
    set OPENAQ_API_KEY=<your_key>   (Windows)
    export OPENAQ_API_KEY=<your_key> (Linux/macOS)
Free keys are available at https://explore.openaq.org/register
"""

import os
import pathlib
import requests
import pandas as pd

BASE_URL = "https://api.openaq.org/v3"

CITIES = [
    {"name": "London",     "lat": 51.51, "lon": -0.13},
    {"name": "Birmingham", "lat": 52.48, "lon": -1.90},
    {"name": "Manchester", "lat": 53.48, "lon": -2.24},
    {"name": "Leeds",      "lat": 53.80, "lon": -1.55},
    {"name": "Edinburgh",  "lat": 55.95, "lon": -3.19},
]


def _session() -> requests.Session:
    s = requests.Session()
    api_key = os.environ.get("OPENAQ_API_KEY", "")
    if api_key:
        s.headers.update({"X-API-Key": api_key})
    return s


def _find_nearest_pm25_location(session: requests.Session, lat: float, lon: float) -> tuple[dict, int] | tuple[None, None]:
    """Return (location, pm25_sensor_id) for the nearest station with a PM2.5 sensor."""
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": 15000,
        "limit": 5,
    }
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()

    for location in resp.json().get("results", []):
        for sensor in location.get("sensors", []):
            if sensor.get("parameter", {}).get("name", "").lower() == "pm25":
                return location, sensor["id"]

    return None, None


def _get_latest_pm25(session: requests.Session, location_id: int, sensor_id: int) -> dict | None:
    """Return the latest measurement dict for a specific sensor from /locations/{id}/latest."""
    url = f"{BASE_URL}/locations/{location_id}/latest"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    for measurement in resp.json().get("results", []):
        if measurement.get("sensorsId") == sensor_id:
            return measurement

    return None


def fetch_live_readings() -> pd.DataFrame:
    session = _session()
    rows = []

    for city in CITIES:
        city_name = city["name"]
        try:
            location, sensor_id = _find_nearest_pm25_location(session, city["lat"], city["lon"])
            if location is None:
                print(f"  {city_name}: no PM2.5 station found within 15 km")
                continue

            location_id = location["id"]
            measurement = _get_latest_pm25(session, location_id, sensor_id)
            if measurement is None:
                print(f"  {city_name}: no latest reading for sensor {sensor_id} at '{location.get('name')}'")
                continue

            last_updated = measurement.get("datetime", {}).get("utc")
            coords = location.get("coordinates", {})
            pm25_value = measurement.get("value")

            rows.append(
                {
                    "city": city_name,
                    "station_name": location.get("name", "unknown"),
                    "pm25_current": pm25_value,
                    "latitude": coords.get("latitude"),
                    "longitude": coords.get("longitude"),
                    "last_updated": last_updated,
                }
            )
            print(f"  {city_name}: {pm25_value} µg/m³ at '{location.get('name')}' ({last_updated})")

        except requests.HTTPError as exc:
            print(f"  {city_name}: HTTP error — {exc}")
        except Exception as exc:
            print(f"  {city_name}: unexpected error — {exc}")

    return pd.DataFrame(
        rows,
        columns=["city", "station_name", "pm25_current", "latitude", "longitude", "last_updated"],
    )


def main() -> None:
    print("Fetching live PM2.5 readings …")
    df = fetch_live_readings()

    out_path = pathlib.Path(__file__).parent.parent / "data" / "processed" / "live_readings.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"\nSaved {len(df)} row(s) to {out_path}\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
