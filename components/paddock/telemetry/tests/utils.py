import os
import pickle
from pprint import pprint

import numpy as np
import pandas as pd

from telemetry.influx import Influx
from telemetry.models import Lap


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
    file_path = f"{dir_path}/data/session_{session_id}_df.csv.gz"

    if os.path.exists(file_path):
        session_df = read_dataframe(file_path)
    else:
        influx = Influx()
        session_df = influx.session_df(session_id, measurement=measurement, bucket=bucket, start="-10y")
        save_dataframe(session_df, file_path)

    return process_dataframe(session_df)


def get_lap_df(lap_id, measurement="fast_laps", bucket="fast_laps"):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/lap_{lap_id}_df.csv.gz"

    if os.path.exists(file_path):
        lap_df = read_dataframe(file_path)
    else:
        influx = Influx()
        lap = Lap.objects.get(id=lap_id)
        laps = influx.telemetry_for_laps([lap], measurement=measurement, bucket=bucket)
        lap_df = laps[0]
        save_dataframe(lap_df, file_path)

    return process_dataframe(lap_df)


def read_responses(file_name, pickled=False):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/responses_{file_name}.txt"
    if pickled:
        with open(file_path, "rb") as f:
            responses = pickle.load(
                f
            )  # nosec FIXME #312 https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b301-pickle
        return responses

    with open(file_path, "r") as f:
        responses = eval(
            f.read()
        )  # nosec FIXME #313 https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b307-eval
    return responses


def save_responses(responses, file_name, pickled=False):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{dir_path}/data/responses_{file_name}.txt"
    if pickled:
        with open(file_path, "wb") as f:
            pickle.dump(responses, f)
        return

    with open(file_path, "w") as f:
        pprint(responses, stream=f, width=200)
