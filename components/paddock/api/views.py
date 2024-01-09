import json
import os
import tempfile

import numpy as np
import pandas as pd
from django.http import JsonResponse
from django.views import View

from telemetry.analyzer import Analyzer
from telemetry.influx import Influx


class SessionView(View):
    template_name = "session.html"
    temp_dir = tempfile.mkdtemp()

    def read_dataframe(self, file_path):
        return pd.read_csv(file_path, compression="gzip", parse_dates=["_time"])

    def save_dataframe(self, df, file_path):
        df.to_csv(file_path, compression="gzip", index=False)

    def process_dataframe(self, df):
        df = df.sort_values(by="_time")
        df = df.replace(np.nan, None)
        return df

    def get_session_df(self, session_id, measurement="laps_cc", bucket="racing"):
        file_path = f"{self.temp_dir}/session_{session_id}_df.csv.gz"

        if os.path.exists(file_path) or False:
            session_df = self.read_dataframe(file_path)
        else:
            influx = Influx()
            session_df = influx.session_df(session_id, measurement=measurement, bucket=bucket, start="-10y")
            self.save_dataframe(session_df, file_path)

        return self.process_dataframe(session_df)

    def get(self, request, session_id=0, *args, **kwargs):
        df = self.get_session_df(session_id)

        # only return the columns we need: "SpeedMs", "Throttle", "Brake", "DistanceRoundTrack"
        columns = ["SpeedMs", "Throttle", "Brake", "DistanceRoundTrack", "CurrentLap"]
        # add WorldPosition_x, WorldPosition_y, WorldPosition_z to columns
        columns += ["WorldPosition_x", "WorldPosition_y", "WorldPosition_z"]

        df = df[columns]

        # resample df to 1 meter intervals
        # FIXME this resampling is based on just one lap
        analyzer = Analyzer()
        df = analyzer.resample(df, columns=columns, freq=1)

        # Compression:
        # Compress the JSON response. Django can be configured to gzip responses, which can significantly reduce the response size.
        # Make sure your frontend can handle the decompression, which is typically handled automatically by modern browsers.

        # render the dataframe as json
        df_json = df.to_json(orient="split", date_format="iso")

        df_dict = json.loads(df_json)

        return JsonResponse(df_dict, safe=False)
