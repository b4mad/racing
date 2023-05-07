from telemetry.influx import Influx
from telemetry.models import Lap
import os
import pandas as pd
import numpy as np


def get_session_df(session_id, measurement="fast_laps", bucket="fast_laps"):
    measurement = measurement
    bucket = bucket
    start = "-10y"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/{session_id}_df.csv.gz"

    if os.path.exists(file_path):
        session_df = pd.read_csv(file_path, compression="gzip", parse_dates=["_time"])
        # session_df['_time'] = pd.to_datetime(session_df['_time'])
    else:
        influx = Influx()
        session_df = influx.session_df(
            session_id, measurement=measurement, bucket=bucket, start=start
        )
        session_df.to_csv(file_path, compression="gzip", index=False)

    # Call the signal method with values from the dataframe
    # sort session_df by time
    session_df = session_df.sort_values(by="_time")
    session_df = session_df.replace(np.nan, None)
    return session_df

def get_lap_df(lap_id, measurement="fast_laps", bucket="fast_laps"):
    measurement = measurement
    bucket = bucket
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/{lap_id}_df.csv.gz"

    if os.path.exists(file_path):
        lap_df = pd.read_csv(file_path, compression="gzip", parse_dates=["_time"])
        # session_df['_time'] = pd.to_datetime(session_df['_time'])
    else:
        influx = Influx()
        lap = Lap.objects.get(id=lap_id)
        laps = influx.telemetry_for_laps(
            [lap], measurement=measurement, bucket=bucket
        )
        lap_df = laps[0]
        lap_df.to_csv(file_path, compression="gzip", index=False)

    # Call the signal method with values from the dataframe
    # sort session_df by time
    lap_df = lap_df.sort_values(by="_time")
    lap_df = lap_df.replace(np.nan, None)
    return lap_df

