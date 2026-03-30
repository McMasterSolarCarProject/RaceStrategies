import sqlite3
from datetime import datetime, timedelta, timezone

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import numpy as np


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
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
        "hourly": "temperature_2m",
        "minutely_15": [
            "temperature_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "direct_normal_irradiance",  # replaces shortwave_radiation_instant
            "diffuse_radiation",
            "wind_direction_10m",
        ],
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

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
            "direct_normal_irradiance": minutely_15.Variables(3).ValuesAsNumpy(),
            "diffuse_radiation": minutely_15.Variables(4).ValuesAsNumpy(),
            "wind_direction_10m": minutely_15.Variables(5).ValuesAsNumpy(),
        }
    )

    #print(df.shortwave_radiation.to_string(index=False))

    result = df[df["date"] == pd.to_datetime(rounded_time)]
    return result


def weather_assess():
    # TODO: Make ASC_2024.sqlite a parameter instead of hardcoding it here
    conn = sqlite3.connect("ASC_2024.sqlite")
    
    df = pd.read_sql_query("SELECT * FROM route_data", conn)

    if "distance" not in df.columns:
        raise ValueError("No 'distance' column in the table.")

    max_distance = df["distance"].max()
    intervals = list(range(0, int(max_distance) + 12500, 12500))
    dt_start = datetime.now(timezone.utc)

    #Clear the columns
    df['ghi'] = np.nan
    df['wind_speed'] = np.nan
    df['wind_dir_sin'] = np.nan
    df['wind_dir_cos'] = np.nan

    print(f"Fetching API data for {len(intervals)} anchor points...")

    # Grab the list of location points for the api
    for interval in intervals:
        idx = (df["distance"] - interval).abs().idxmin()
        target_row = df.loc[idx]

        blocks_passed = int(interval // 12500)
        current_dt = dt_start + timedelta(minutes=15 * blocks_passed)

        data = retrieve_data(target_row["lat"], target_row["lon"], current_dt)

        if data.empty:
            print(f"No data at {interval}m - skipping anchor.")
            continue

        # Pin the exact API data to this specific row index
        df.at[idx, 'ghi'] = float(data["shortwave_radiation"].iloc[0])
        df.at[idx, 'dni'] = float(data["direct_normal_irradiance"].iloc[0])
        df.at[idx, 'dhi'] = float(data["diffuse_radiation"].iloc[0])
        df.at[idx, 'wind_speed'] = float(data["wind_speed_10m"].iloc[0])

        # Convert wind direction into safe vector components for circular interpolation
        wind_dir = float(data["wind_direction_10m"].iloc[0])
        df.at[idx, 'wind_dir_sin'] = np.sin(np.radians(wind_dir))
        df.at[idx, 'wind_dir_cos'] = np.cos(np.radians(wind_dir))

    print("Interpolating smooth gradients between anchor points...")

    # Set distance as the index to interpolate based on distance, not segment_id
    df.set_index('distance', inplace=True)

    # Perform the mathematical interpolation across all NaN rows
    df['ghi'] = df['ghi'].interpolate(method='index')
    df['dni'] = df['dni'].interpolate(method='index')
    df['dhi'] = df['dhi'].interpolate(method='index')
    df['wind_speed'] = df['wind_speed'].interpolate(method='index')
    df['wind_dir_sin'] = df['wind_dir_sin'].interpolate(method='index')
    df['wind_dir_cos'] = df['wind_dir_cos'].interpolate(method='index')

    # Reconstruct the wind direction angle from the smoothed vectors
    df['wind_dir'] = (np.degrees(np.arctan2(df['wind_dir_sin'], df['wind_dir_cos'])) + 360) % 360

    # Clean up the dataframe
    df.drop(columns=['wind_dir_sin', 'wind_dir_cos'], inplace=True)
    df.reset_index(inplace=True)

    # Fill any straggling NaNs at the very end of the route past the last 12.5km multiple
    df = df.bfill().ffill()

    # Overwrite the SQLite table with the fully populated, smoothed dataframe
    df.to_sql("route_data", conn, if_exists="replace", index=False)
    conn.close()
    
    print("GHI and windspeed interpolation complete")
weather_assess()