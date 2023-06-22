from pprint import pprint  # noqa

import numpy as np
import pandas as pd
from django.test import TransactionTestCase

from telemetry.analyzer import Analyzer
from telemetry.fast_lap_analyzer import FastLapAnalyzer

from .utils import get_lap_df, read_responses, save_responses  # noqa


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
        #  Processing iRacing - fuji nochicane - Ferrari 488 GT3 Evo 2020
        #    track.id 409 car.id 9
        #    session 1682107191 lap.id 37672 number 4
        #    length 4459 time 97.0107 valid True
        #    start 2023-04-21 22:04:53.148000+00:00 end 2023-04-21 22:06:30.157000+00:00
        return
        lap_id = 37672
        lap_df = get_lap_df(lap_id)
        fast_lap_analyzer = FastLapAnalyzer()

        (track_info, data) = fast_lap_analyzer.analyze_df(lap_df)

        segments = read_responses("fastlap_analyzer_37672", pickled=True)

        # save_responses(track_info, "fastlap_analyzer_37672", pickled=True)

        # pprint(track_info, width=200)
        self.assertEqual(track_info, segments)

    def test_analyze_2(self):
        # Processing Automobilista 2 Road_America:Road_America_RC
        #    Reynard 95i Ford-Cosworth
        #    : session 1683388042 : lap.id 40781 : length 6435 : time 104.26001
        return
        lap_id = 40781
        lap_df = get_lap_df(lap_id)
        fast_lap_analyzer = FastLapAnalyzer()

        (track_info, data) = fast_lap_analyzer.analyze_df(lap_df)

        segments = read_responses("fastlap_analyzer_40781", pickled=True)

        # save_responses(track_info, "fastlap_analyzer_40781", pickled=True)

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
