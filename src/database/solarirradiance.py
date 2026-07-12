import sqlite3
from datetime import datetime, timedelta, timezone

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import numpy as np

cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://api.open-meteo.com/v1/forecast"

def round_to_nearest_15_minutes(dt):
    dt = dt.replace(second=0, microsecond=0)
    remainder = dt.minute % 15

    if remainder < 7.5:
        dt -= timedelta(minutes=remainder)
    else:
        dt += timedelta(minutes=(15 - remainder))

    return dt

def retrieve_data(lat, lon, time):
    rounded_time = round_to_nearest_15_minutes(time)

    params = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": [
            "temperature_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "shortwave_radiation_instant",
            "wind_direction_10m",
            "direct_normal_irradiance",
            "diffuse_radiation"
        ],
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
    except Exception as e:
        print(f"Api request failed at {lat}, {lon}")
        print(f"Reason: {e}")
        return pd.DataFrame()

    minutely_15 = response.Minutely15()

    df = pd.DataFrame(
        {
            "date": pd.date_range(
                start=pd.to_datetime(minutely_15.Time(), unit="s", utc=True),
                end=pd.to_datetime(minutely_15.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=minutely_15.Interval()),
                inclusive="left",
            ),
            "temperature_2m": minutely_15.Variables(0).ValuesAsNumpy(),
            "wind_speed_10m": minutely_15.Variables(1).ValuesAsNumpy(),
            "shortwave_radiation": minutely_15.Variables(2).ValuesAsNumpy(),
            "shortwave_radiation_instant": minutely_15.Variables(3).ValuesAsNumpy(),
            "wind_direction_10m": minutely_15.Variables(4).ValuesAsNumpy(),
            "direct_normal_irradiance": minutely_15.Variables(5).ValuesAsNumpy(),
            "diffuse_radiation": minutely_15.Variables(6).ValuesAsNumpy(),
            
        }
    )

    result = df[df["date"] == pd.to_datetime(rounded_time)]
    return result

def weather_assess(db_path="ASC_2024.sqlite", start_distance=0):
    conn = sqlite3.connect(db_path)
    
    df = pd.read_sql_query("SELECT * FROM route_row", conn)

    if "distance" not in df.columns:
        raise ValueError("No 'distance' column in the table.")

    max_distance = df["distance"].max()
    
    start_interval = int(start_distance // 12500) * 12500
    intervals = list(range(start_interval, int(max_distance) + 12500, 12500))
    dt_start = datetime.now(timezone.utc)

    update_mask = df['distance'] >= start_interval
    for col in ['ghi', 'dni', 'dhi', 'wind_speed', 'wind_dir_sin', 'wind_dir_cos']:
        df.loc[update_mask, col] = np.nan

    print(f"Fetching API data for {len(intervals)} anchor points starting from {start_interval}m...")

    for interval in intervals:
        idx = (df["distance"] - interval).abs().idxmin()
        target_row = df.loc[idx]

        blocks_passed = int((interval - start_interval) // 12500)
        current_dt = dt_start + timedelta(minutes=15 * blocks_passed)

        data = retrieve_data(target_row["lat"], target_row["lon"], current_dt)

        if data.empty:
            print(f"No data at {interval}m - skipping anchor.")
            continue

        df.at[idx, 'ghi'] = float(data["shortwave_radiation"].iloc[0])
        df.at[idx, 'dni'] = float(data["direct_normal_irradiance"].iloc[0])
        df.at[idx, 'dhi'] = float(data["diffuse_radiation"].iloc[0])
        df.at[idx, 'wind_speed'] = float(data["wind_speed_10m"].iloc[0])

        wind_dir = float(data["wind_direction_10m"].iloc[0])
        df.at[idx, 'wind_dir_sin'] = np.sin(np.radians(wind_dir))
        df.at[idx, 'wind_dir_cos'] = np.cos(np.radians(wind_dir))

    print("Interpolating smooth gradients between anchor points...")

    weather_cols = ['ghi', 'dni', 'dhi', 'wind_speed', 'wind_dir_sin', 'wind_dir_cos']
    for col in weather_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.set_index('distance', inplace=True)

    df['ghi'] = df['ghi'].interpolate(method='index')
    df['dni'] = df['dni'].interpolate(method='index')
    df['dhi'] = df['dhi'].interpolate(method='index')
    df['wind_speed'] = df['wind_speed'].interpolate(method='index')
    df['wind_dir_sin'] = df['wind_dir_sin'].interpolate(method='index')
    df['wind_dir_cos'] = df['wind_dir_cos'].interpolate(method='index')

    df['wind_dir'] = (np.degrees(np.arctan2(df['wind_dir_sin'], df['wind_dir_cos'])) + 360) % 360

    df.drop(columns=['wind_dir_sin', 'wind_dir_cos'], inplace=True)
    df.reset_index(inplace=True)

    weather_cols = ['ghi', 'dni', 'dhi', 'wind_speed', 'wind_dir']
    df[weather_cols] = df[weather_cols].bfill().ffill()

    # Convert the dataframe slice to a native Python list of tuples
    update_data = list(df[['ghi', 'dni', 'dhi', 'wind_speed', 'wind_dir', 'placemark_name', 'id']].itertuples(index=False, name=None))
    
    cursor = conn.cursor()
    cursor.executemany(
        '''UPDATE route_row 
           SET ghi = ?, dni = ?, dhi = ?, wind_speed = ?, wind_dir = ? 
           WHERE placemark_name = ? AND id = ?''',
        update_data
    )
    conn.commit()
    conn.close()
    
    print("GHI, DNI, DHI and windspeed interpolation complete")

if __name__ == "__main__":
    weather_assess()