from telemetry.influx import Influx
from telemetry.models import Lap
import os
import pandas as pd
import numpy as np


def read_dataframe(file_path):
    return pd.read_csv(file_path, compression="gzip", parse_dates=["_time"])


def save_dataframe(df, file_path):
    df.to_csv(file_path, compression="gzip", index=False)


def process_dataframe(df):
    df = df.sort_values(by="_time")
    df = df.replace(np.nan, None)
    return df


def get_session_df(session_id, measurement="fast_laps", bucket="fast_laps"):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/{session_id}_df.csv.gz"

    if os.path.exists(file_path):
        session_df = read_dataframe(file_path)
    else:
        influx = Influx()
        session_df = influx.session_df(session_id, measurement=measurement, bucket=bucket, start="-10y")
        save_dataframe(session_df, file_path)

    return process_dataframe(session_df)


def get_lap_df(lap_id, measurement="fast_laps", bucket="fast_laps"):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/{lap_id}_df.csv.gz"

    if os.path.exists(file_path):
        lap_df = read_dataframe(file_path)
    else:
        influx = Influx()
        lap = Lap.objects.get(id=lap_id)
        laps = influx.telemetry_for_laps([lap], measurement=measurement, bucket=bucket)
        lap_df = laps[0]
        save_dataframe(lap_df, file_path)

    return process_dataframe(lap_df)
