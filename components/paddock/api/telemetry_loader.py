import os
import tempfile

import numpy as np
import pandas as pd

from telemetry.analyzer import Analyzer
from telemetry.influx import Influx
from telemetry.models import Lap


class TelemetryLoader:
    temp_dir = tempfile.mkdtemp()

    def __init__(self, caching=False):
        self.caching = caching
        pass

    def read_dataframe(self, file_path):
        return pd.read_csv(file_path, compression="gzip", parse_dates=["_time"])

    def save_dataframe(self, df, file_path):
        df.to_csv(file_path, compression="gzip", index=False)

    def process_dataframe(self, df):
        df = df.sort_values(by="_time")
        df = df.replace(np.nan, None)

        # only return the columns we need: "SpeedMs", "Throttle", "Brake", "DistanceRoundTrack"
        columns = ["SpeedMs", "Throttle", "Brake", "DistanceRoundTrack", "CurrentLap"]

        # check if the session contains position data
        if "WorldPosition_x" in df.columns:
            columns += ["WorldPosition_x", "WorldPosition_y", "WorldPosition_z"]

        for field in ["Yaw", "Pitch", "Roll"]:
            if field in df.columns:
                columns += [field]

        df = df[columns]

        # resample df to 1 meter intervals
        # FIXME this resampling is based on just one lap
        analyzer = Analyzer()
        df = analyzer.resample(df, columns=columns, freq=1)
        # change CurrentLap to int
        # df["CurrentLap"] = df["CurrentLap"].astype(int)

        return df

    def get_lap_df(self, lap_id, measurement="laps_cc", bucket="racing"):
        # make sure the lap_id is an integer
        lap_id = int(lap_id)
        # fetch the lap from the database
        lap = Lap.objects.get(id=lap_id)

        influx = Influx()
        lap_df = influx.telemetry_for_laps([lap], measurement=measurement, bucket=bucket)

        df = self.process_dataframe(lap_df[0])

        return df

    def get_session_df(self, session_id, measurement="laps_cc", bucket="racing"):
        # make sure the session_id is an integer
        session_id = int(session_id)
        file_path = f"{self.temp_dir}/session_{session_id}_df.csv.gz"

        if self.caching and os.path.exists(file_path):
            session_df = self.read_dataframe(file_path)
        else:
            influx = Influx()
            # aggregate = ""
            # if self.caching:
            #     aggregate = "1s"
            session_df = influx.session_df(
                session_id, measurement=measurement, bucket=bucket, start="-10y", aggregate="1s"
            )
            if self.caching:
                self.save_dataframe(session_df, file_path)

        df = self.process_dataframe(session_df)

        return df
