from django.test import TestCase
from telemetry.pitcrew.session import Session, Lap
from telemetry.influx import Influx
import os
import pandas as pd
from pprint import pprint


class TestSession(TestCase):
    def _test_session(
        self, session_id, expected_laps, measurement="fast_laps", bucket="fast_laps"
    ):
        influx = Influx()

        measurement = measurement
        bucket = bucket
        start = "-10y"
        file_path = f"telemetry/test_data/{session_id}_df.csv.gz"

        if os.path.exists(file_path):
            session_df = pd.read_csv(
                file_path, compression="gzip", parse_dates=["_time"]
            )
            # session_df['_time'] = pd.to_datetime(session_df['_time'])
        else:
            session_df = influx.session_df(
                session_id, measurement=measurement, bucket=bucket, start=start
            )
            session_df.to_csv(file_path, compression="gzip", index=False)

        # Create an instance of the Session class
        test_session = Session(666)

        # Call the signal method with values from the dataframe
        # sort session_df by time
        session_df = session_df.sort_values(by="_time")
        for index, row in session_df.iterrows():
            now = row["_time"]
            test_session.signal(row, now)

        pprint(test_session.laps)
        # Iterate over the expected_laps dictionary and compare to the test_session.laps
        for lap_number, expected_lap in expected_laps.items():
            lap = test_session.laps[lap_number]

            self.assertEqual(lap.number, expected_lap.number)
            self.assertEqual(lap.time, expected_lap.time)
            self.assertEqual(lap.valid, expected_lap.valid)

            if lap.time != -1:
                # the difference between lap.end and lap.start should be equal to lap.time
                time_delta = lap.end - lap.start
                self.assertAlmostEqual(time_delta.total_seconds(), lap.time, places=1)

    def test_iracing(self):
        # measurement = "fast_laps"
        # bucket = "fast_laps"
        # start = "-10y"
        session_id = "1681021274"

        # For this session the following laps are valid:
        # 1 valid: during outlap lap_number is 1, remains 1 on crossing finish line
        # 2 invalid: penalty during lap, reset to pits, lap_number is remains 2 on outlap
        # 3 valid: lap_number changes to 3 on crossing finish line
        # 4 valid: lap_number changes to 4 on crossing finish line
        # 5 valid: lap_number changes to 5 on crossing finish line
        # 6 invalid: penalty during lap, no reset to pits
        # 7 invalid: lap_number changes to 7 on crossing finish line,
        #            no penalty during lap, but "PreviousLapWasValid" is false
        # 8 invalid: penalty during lap, reset to pits, lap_number is remains 8 on outlap
        # 9 invalid: penalty during lap, no reset to pits
        # 10 invalid: penalty during lap, eset to pits
        # a lap time of -1 indicates an outlap

        expected_laps = {
            1: Lap(1, time=100.818, valid=True),
            2: Lap(2, time=-1, valid=False),
            3: Lap(3, time=101.0466, valid=True),
            4: Lap(4, time=100.823, valid=True),
            5: Lap(5, time=99.4026, valid=True),
            6: Lap(6, time=107.9166, valid=False),
            7: Lap(7, time=99.0674, valid=False),
            8: Lap(8, time=-1, valid=False),
            9: Lap(9, time=101.7361, valid=False),
            10: Lap(10, time=-1, valid=False),
        }
        self._test_session(session_id, expected_laps)
