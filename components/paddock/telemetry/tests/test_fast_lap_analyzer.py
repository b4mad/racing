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
            {
                "brake_features": {
                    "end": 727.92,
                    "force": 0.77,
                    "max_end": 687.92,
                    "max_high": 0.83,
                    "max_low": 0.7,
                    "max_start": 591.91,
                    "start": 577.91,
                },
                "end": 1184,
                "force": 77.0,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 72.51938,
                "start": 555,
                "throttle_features": {
                    "end": 777.92,
                    "force": 0.0,
                    "max_end": 763.92,
                    "max_high": 0.09,
                    "max_low": 0.0,
                    "max_start": 576.91,
                    "start": 565.91,
                },
            },
            {
                "brake_features": {
                    "end": 1260.94,
                    "force": 0.38,
                    "max_end": 1247.94,
                    "max_high": 0.42,
                    "max_low": 0.31,
                    "max_start": 1213.94,
                    "start": 1208.94,
                },
                "end": 1450,
                "force": 38.0,
                "gear": 4.0,
                "gear_features": {"gear": 4.0},
                "mark": "brake",
                "speed": 58.5803871,
                "start": 1185,
                "throttle_features": {
                    "end": 1363.94,
                    "force": 0.01,
                    "max_end": 1344.94,
                    "max_high": 0.1,
                    "max_low": 0.0,
                    "max_start": 1206.94,
                    "start": 1195.94,
                },
            },
            {
                "brake_features": {},
                "end": 1863,
                "force": 0.0,
                "gear": 4.0,
                "gear_features": {"gear": 4.0},
                "mark": "throttle",
                "speed": 51.1693649,
                "start": 1451,
                "throttle_features": {
                    "end": 1744.96,
                    "force": 0.0,
                    "max_end": 1686.95,
                    "max_high": 0.09,
                    "max_low": 0.0,
                    "max_start": 1563.95,
                    "start": 1461.95,
                },
            },
            {
                "brake_features": {
                    "end": 1943.96,
                    "force": 0.55,
                    "max_end": 1917.96,
                    "max_high": 0.6,
                    "max_low": 0.5,
                    "max_start": 1891.96,
                    "start": 1881.96,
                },
                "end": 2659,
                "force": 55.00000000000001,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 50.30912,
                "start": 1864,
                "throttle_features": {
                    "end": 2029.97,
                    "force": 0.0,
                    "max_end": 1985.96,
                    "max_high": 0.09,
                    "max_low": 0.0,
                    "max_start": 1881.96,
                    "start": 1874.96,
                },
            },
            {
                "brake_features": {
                    "end": 2795.99,
                    "force": 0.74,
                    "max_end": 2727.99,
                    "max_high": 0.76,
                    "max_low": 0.7,
                    "max_start": 2699.99,
                    "start": 2680.99,
                },
                "end": 2957,
                "force": 74.0,
                "gear": 4.0,
                "gear_features": {"gear": 4.0},
                "mark": "brake",
                "speed": 65.6388855,
                "start": 2660,
                "throttle_features": {
                    "end": 2826.99,
                    "force": 0.0,
                    "max_end": 2807.99,
                    "max_high": 0.04,
                    "max_low": 0.0,
                    "max_start": 2678.99,
                    "start": 2670.99,
                },
            },
            {
                "brake_features": {
                    "end": 3062.0,
                    "force": 0.3,
                    "max_end": 3045.0,
                    "max_high": 0.39,
                    "max_low": 0.21,
                    "max_start": 2981.0,
                    "start": 2979.0,
                },
                "end": 3188,
                "force": 30.0,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 47.4273,
                "start": 2958,
                "throttle_features": {
                    "end": 3114.01,
                    "force": 0.01,
                    "max_end": 3070.0,
                    "max_high": 0.1,
                    "max_low": 0.0,
                    "max_start": 2976.0,
                    "start": 2968.0,
                },
            },
            {
                "brake_features": {
                    "end": 3291.01,
                    "force": 0.2,
                    "max_end": 3290.01,
                    "max_high": 0.27,
                    "max_low": 0.11,
                    "max_start": 3238.01,
                    "start": 3238.01,
                },
                "end": 3452,
                "force": 20.0,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 38.8867264,
                "start": 3189,
                "throttle_features": {
                    "end": 3376.01,
                    "force": 0.0,
                    "max_end": 3316.01,
                    "max_high": 0.08,
                    "max_low": 0.0,
                    "max_start": 3213.01,
                    "start": 3199.01,
                },
            },
            {
                "brake_features": {
                    "end": 3542.02,
                    "force": 0.17,
                    "max_end": 3541.02,
                    "max_high": 0.2,
                    "max_low": 0.11,
                    "max_start": 3497.02,
                    "start": 3497.02,
                },
                "end": 554,
                "force": 17.0,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 40.5536842,
                "start": 3453,
                "throttle_features": {
                    "end": 3640.02,
                    "force": 0.0,
                    "max_end": 3619.02,
                    "max_high": 0.06,
                    "max_low": 0.0,
                    "max_start": 3488.02,
                    "start": 3463.02,
                },
            },
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
            {
                "brake_features": {
                    "end": 589.11,
                    "force": 0.97,
                    "max_end": 550.12,
                    "max_high": 1.0,
                    "max_low": 0.93,
                    "max_start": 505.12,
                    "start": 505.12,
                },
                "end": 668,
                "force": 97.0,
                "gear": 3.0,
                "gear_features": {"gear": 3.0},
                "mark": "brake",
                "speed": 84.99187,
                "start": 486,
                "throttle_features": {
                    "end": 667.1,
                    "force": 0.0,
                    "max_end": 594.11,
                    "max_high": 0.0,
                    "max_low": 0.0,
                    "max_start": 505.12,
                    "start": 496.13,
                },
            },
            {
                "brake_features": {},
                "end": 981,
                "force": 49.0,
                "gear": 3.0,
                "gear_features": {"gear": 3.0},
                "mark": "throttle",
                "speed": 51.6653442,
                "start": 669,
                "throttle_features": {
                    "end": 674.1,
                    "force": 0.49,
                    "max_end": 673.1,
                    "max_high": 0.49,
                    "max_low": 0.49,
                    "max_start": 669.1,
                    "start": 669.1,
                },
            },
            {
                "brake_features": {
                    "end": 1081.03,
                    "force": 0.8,
                    "max_end": 1060.03,
                    "max_high": 0.83,
                    "max_low": 0.7,
                    "max_start": 1012.04,
                    "start": 992.04,
                },
                "end": 2073,
                "force": 80.0,
                "gear": 2.0,
                "gear_features": {"gear": 2.0},
                "mark": "brake",
                "speed": 74.39352,
                "start": 982,
                "throttle_features": {
                    "end": 1194.01,
                    "force": 0.0,
                    "max_end": 1117.02,
                    "max_high": 0.0,
                    "max_low": 0.0,
                    "max_start": 1000.04,
                    "start": 992.04,
                },
            },
            {
                "brake_features": {
                    "end": 2215.83,
                    "force": 0.97,
                    "max_end": 2137.85,
                    "max_high": 1.0,
                    "max_low": 0.93,
                    "max_start": 2094.85,
                    "start": 2094.85,
                },
                "end": 2473,
                "force": 97.0,
                "gear": 1.0,
                "gear_features": {"gear": 1.0},
                "mark": "brake",
                "speed": 83.39049,
                "start": 2074,
                "throttle_features": {
                    "end": 2345.81,
                    "force": 0.0,
                    "max_end": 2290.82,
                    "max_high": 0.03,
                    "max_low": 0.0,
                    "max_start": 2094.85,
                    "start": 2084.86,
                },
            },
            {
                "brake_features": {
                    "end": 2566.77,
                    "force": 0.49,
                    "max_end": 2547.78,
                    "max_high": 0.56,
                    "max_low": 0.41,
                    "max_start": 2514.78,
                    "start": 2491.79,
                },
                "end": 2767,
                "force": 49.0,
                "gear": 1.0,
                "gear_features": {"gear": 1.0},
                "mark": "brake",
                "speed": 57.91152,
                "start": 2474,
                "throttle_features": {
                    "end": 2656.76,
                    "force": 0.0,
                    "max_end": 2580.77,
                    "max_high": 0.08,
                    "max_low": 0.0,
                    "max_start": 2491.79,
                    "start": 2484.79,
                },
            },
            {
                "brake_features": {},
                "end": 3096,
                "force": 37.0,
                "gear": 3.0,
                "gear_features": {"gear": 3.0},
                "mark": "throttle",
                "speed": 58.8016357,
                "start": 2768,
                "throttle_features": {
                    "end": 2863.72,
                    "force": 0.37,
                    "max_end": 2796.74,
                    "max_high": 0.38,
                    "max_low": 0.37,
                    "max_start": 2784.74,
                    "start": 2778.74,
                },
            },
            {
                "brake_features": {
                    "end": 3227.66,
                    "force": 0.85,
                    "max_end": 3191.67,
                    "max_high": 0.87,
                    "max_low": 0.84,
                    "max_start": 3125.68,
                    "start": 3116.68,
                },
                "end": 3399,
                "force": 85.0,
                "gear": 1.0,
                "gear_features": {"gear": 1.0},
                "mark": "brake",
                "speed": 74.2467957,
                "start": 3097,
                "throttle_features": {
                    "end": 3299.65,
                    "force": 0.0,
                    "max_end": 3253.66,
                    "max_high": 0.0,
                    "max_low": 0.0,
                    "max_start": 3116.68,
                    "start": 3107.68,
                },
            },
            {
                "brake_features": {},
                "end": 4932,
                "force": 33.0,
                "gear": 3.0,
                "gear_features": {"gear": 3.0},
                "mark": "throttle",
                "speed": 57.1214752,
                "start": 3400,
                "throttle_features": {
                    "end": 3726.58,
                    "force": 0.33,
                    "max_end": 3674.59,
                    "max_high": 0.4,
                    "max_low": 0.3,
                    "max_start": 3481.62,
                    "start": 3410.63,
                },
            },
            {
                "brake_features": {
                    "end": 5061.35,
                    "force": 0.98,
                    "max_end": 5022.36,
                    "max_high": 1.0,
                    "max_low": 0.9,
                    "max_start": 4943.37,
                    "start": 4943.37,
                },
                "end": 485,
                "force": 98.0,
                "gear": 1.0,
                "gear_features": {"gear": 1.0},
                "mark": "brake",
                "speed": 85.330925,
                "start": 4933,
                "throttle_features": {
                    "end": 5161.33,
                    "force": 0.01,
                    "max_end": 5096.34,
                    "max_high": 0.05,
                    "max_low": 0.0,
                    "max_start": 4943.37,
                    "start": 4943.37,
                },
            },
        ]

        (track_info, data) = fast_lap_analyzer.analyze_df(lap_df)
        # pprint(track_info, width=200)
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
