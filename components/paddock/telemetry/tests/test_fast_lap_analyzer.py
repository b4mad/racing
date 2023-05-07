from django.test import TransactionTestCase
from telemetry.fast_lap_analyzer import FastLapAnalyzer
from telemetry.analyzer import Analyzer
from .utils import get_lap_df
from pprint import pprint  # noqa
import pandas as pd
import numpy as np


class TestFastLapAnalyser(TransactionTestCase):
    fixtures = [
        "game.json",
        "track.json",
        "car.json",
        "fastlap.json",
        "fastlapsegment.json",
        "driver.json",
        "coach.json",
        "session.json",
        "lap.json",
        "sessiontype.json",
    ]

    def test_analyze(self):
        # 203 laps for iRacing / fuji nochicane / Ferrari 488 GT3 Evo 2020
        #  median time: 99.5406, median length: 4459
        #  6: 22:08:07 - 22:09:44 97.0942s 4458m valid: True
        #  8: 22:11:22 - 22:13:00 97.1737s 4459m valid: True
        #  5: 22:06:30 - 22:08:07 97.2249s 4459m valid: True
        #  7: 11:34:52 - 11:36:29 97.3034s 4459m valid: True
        #  2: 11:22:52 - 11:24:30 97.6725s 4459m valid: True
        #  7: 13:09:29 - 13:11:06 97.7191s 4459m valid: True
        #  3: 13:22:15 - 13:23:53 97.8917s 4459m valid: True
        #  2: 16:43:49 - 16:45:27 97.924s 4459m valid: True
        #  4: 15:05:04 - 15:06:42 97.9808s 4459m valid: True
        #  Influx: Connected to http://influxdb2.b4mad-racing.svc.cluster.local:8086/
        #  Processing iRacing - fuji nochicane - Ferrari 488 GT3 Evo 2020
        #    track.id 409 car.id 9
        #    session 1682107191 lap.id 37672 number 4
        #    length 4459 time 97.0107 valid True
        #    start 2023-04-21 22:04:53.148000+00:00 end 2023-04-21 22:06:30.157000+00:00
        # Found 5 not increasing indices
        #  mark start end gear force speed
        # 0 brake 573 775 2.0 79.0 17.2
        # 1 brake 1204 1360 4.0 41.0 43.4
        # 2 throttle 1462 1808 4.0 0.0 44.5
        # 3 brake 1877 2027 2.0 59.0 28.8
        # 4 brake 2675 2823 4.0 73.0 37.4
        # 5 brake 2974 3109 2.0 38.0 27.0
        # 6 throttle 3198 3373 2.0 0.0 24.6
        # 7 throttle 3462 3637 2.0 0.0 24.5
        lap_id = 37672
        lap_df = get_lap_df(lap_id)
        fast_lap_analyzer = FastLapAnalyzer()
        segments = [
            {"end": 775, "force": 79.0, "gear": 2.0, "mark": "brake", "speed": 17.2139874, "start": 573},
            {"end": 1360, "force": 41.0, "gear": 4.0, "mark": "brake", "speed": 43.4393044, "start": 1204},
            {"end": 1807, "force": 0.0, "gear": 4.0, "mark": "throttle", "speed": 44.4776535, "start": 1462},
            {"end": 2027, "force": 59.0, "gear": 2.0, "mark": "brake", "speed": 28.81261, "start": 1877},
            {"end": 2823, "force": 73.0, "gear": 4.0, "mark": "brake", "speed": 37.3594437, "start": 2676},
            {"end": 3109, "force": 38.0, "gear": 2.0, "mark": "brake", "speed": 27.04253, "start": 2974},
            {"end": 3374, "force": 0.0, "gear": 2.0, "mark": "throttle", "speed": 24.6307, "start": 3198},
            {"end": 3638, "force": 0.0, "gear": 2.0, "mark": "throttle", "speed": 24.46673, "start": 3462},
        ]

        (track_info, data) = fast_lap_analyzer.analyze_df(lap_df)
        # pprint(track_info, width=200)
        self.assertEqual(track_info, segments)

    def test_analyze_2(self):
        # Processing Automobilista 2 Road_America:Road_America_RC
        #    Reynard 95i Ford-Cosworth
        #    : session 1683388042 : lap.id 40781 : length 6435 : time 104.26001
        lap_id = 40781
        lap_df = get_lap_df(lap_id)
        fast_lap_analyzer = FastLapAnalyzer()
        segments = [
            {"end": 738, "force": 97.0, "gear": 3.0, "mark": "brake", "speed": 51.6653442, "start": 501},
            {"end": 1190, "force": 100.0, "gear": 2.0, "mark": "brake", "speed": 38.2091522, "start": 988},
            {"end": 2342, "force": 97.0, "gear": 1.0, "mark": "brake", "speed": 28.5301781, "start": 2091},
            {"end": 2653, "force": 83.0, "gear": 1.0, "mark": "brake", "speed": 30.9640713, "start": 2488},
            {"end": 2861, "force": 37.0, "gear": 3.0, "mark": "throttle", "speed": 58.16961, "start": 2776},
            {"end": 3296, "force": 88.0, "gear": 1.0, "mark": "brake", "speed": 29.4386826, "start": 3113},
            {"end": 3724, "force": 30.0, "gear": 3.0, "mark": "throttle", "speed": 55.9043846, "start": 3408},
            {"end": 5158, "force": 98.0, "gear": 1.0, "mark": "brake", "speed": 35.71367, "start": 4940},
            {"end": 5386, "force": 15.0, "gear": 3.0, "mark": "throttle", "speed": 61.6778336, "start": 5348},
        ]
        (track_info, data) = fast_lap_analyzer.analyze_df(lap_df)
        pprint(track_info, width=200)
        self.assertEqual(track_info, segments)

    def _create_synthetic_dataframe(self):
        np.random.seed(42)
        distance_round_track = np.linspace(0, 1000, 2000)
        brake = np.random.uniform(0, 1, 2000)
        gear = np.random.randint(0, 6, 2000)

        df = pd.DataFrame({"DistanceRoundTrack": distance_round_track, "Brake": brake, "Gear": gear})
        return df

    def test_resample(self):
        df = self._create_synthetic_dataframe()
        # print(df.head())
        analyzer = Analyzer()
        for freq in [0.5, 1, 2, 2.5]:
            resampled_df = analyzer.resample(df, ["Brake", "Gear"], freq=freq)
            # print(resampled_df.head())
            self.assertEqual(len(resampled_df), 1000 / freq)