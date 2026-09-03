import os
import pathlib
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "dashboard" / ".env")
load_dotenv()

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


def fetch_live_readings() -> pd.DataFrame:
    session = _session()
    rows = []

    for city in CITIES:
        city_name = city["name"]
        lat, lon = city["lat"], city["lon"]
        try:
            url = f"{BASE_URL}/locations"
            params = {
                "coordinates": f"{lat},{lon}",
                "radius": 25000,
                "limit": 10,
            }
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()

            best_reading = None
            for loc in resp.json().get("results", []):
                pm25_sensors = {
                    s["id"]: s for s in loc.get("sensors", [])
                    if s.get("parameter", {}).get("name", "").lower() == "pm25"
                }
                if not pm25_sensors:
                    continue

                loc_id = loc["id"]
                station_name = loc.get("name", "Unknown Station")
                coords = loc.get("coordinates", {})

                try:
                    r2 = session.get(f"{BASE_URL}/locations/{loc_id}/latest", timeout=8)
                    if r2.status_code != 200:
                        continue
                    for m in r2.json().get("results", []):
                        sid = m.get("sensorsId")
                        val = m.get("value")
                        if sid in pm25_sensors and val is not None and val >= 0:
                            ts = m.get("datetime", {})
                            reading_timestamp = ts.get("utc", "") if isinstance(ts, dict) else str(ts)
                            if not best_reading or reading_timestamp > best_reading["last_updated"]:
                                best_reading = {
                                    "city": city_name,
                                    "station_name": station_name,
                                    "pm25_current": float(val),
                                    "latitude": coords.get("latitude", lat),
                                    "longitude": coords.get("longitude", lon),
                                    "last_updated": reading_timestamp,
                                }
                except Exception:
                    continue

            if best_reading:
                rows.append(best_reading)
                print(f"  {city_name}: {best_reading['pm25_current']} µg/m³ at '{best_reading['station_name']}' ({best_reading['last_updated']})")
            else:
                print(f"  {city_name}: no valid PM2.5 readings found within 25 km")

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
