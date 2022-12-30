import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import logging
from .influx import Influx
from .analyzer import Analyzer


class FastLapAnalyzer:
    def __init__(self, laps):
        self.influx = Influx()
        self.analyzer = Analyzer()
        self.laps = laps

    def assert_can_analyze(self):
        # game = self.laps[0].session.game
        # car = self.laps[0].car

        # if game.name == "RaceRoom":
        #     logging.info("RaceRoom not supported, because no SteeringAngle")
        #     return False
        # if game.name == "Assetto Corsa Competizione":
        #     logging.info(
        #         "Assetto Corsa Competizione not supported, because no SteeringAngle"
        #     )
        #     return False
        # if car.name == "Unknown":
        #     logging.info(f"Car {car.name} not supported, skipping")
        #     return False
        return True

    def analyze(self):
        if not self.assert_can_analyze():
            return

        all_laps = self.influx.telemetry_for_laps(self.laps)
        if len(all_laps) == 0:
            return

        laps = self.analyzer.remove_uncorrelated_laps(all_laps, column="SpeedMs")

        # get the max distance for each lap and select the max
        max_distance = np.max([df["DistanceRoundTrack"].max() for df in laps])

        all_minima = []
        for lap_df in laps:
            # extend the lap to 3 times the length
            df = self.analyzer.drop_decreasing(lap_df)
            window_length = 120  # 60 points corresponds to 1 seconds
            if len(df) < window_length:
                # too short, skip
                logging.warning("lap too short, skipping")
                continue
            df = self.analyzer.extend_lap(df)

            # smooth the laps
            df["SpeedMs"] = savgol_filter(df["SpeedMs"], window_length, 2)
            minima = self.analyzer.local_minima(df, column="SpeedMs")
            logging.debug(f"number of minima {len(minima)} for lap {df['id'].iloc[0]}")
            all_minima.append(minima)

        if len(all_minima) == 0:
            return

        centroids_df, labels = self.analyzer.cluster(all_minima, field="SpeedMs")
        centroids_df = centroids_df.sort_values(by=["DistanceRoundTrack"])
        centroids_df = centroids_df.reset_index(drop=True)
        df = centroids_df.copy()

        # apply modulo length to DistanceRoundTrack
        df["DistanceRoundTrack"] = df["DistanceRoundTrack"].mod(max_distance)

        # sort the centroids by DistanceRoundTrack and reset the index
        df = df.sort_values(by=["DistanceRoundTrack"])
        df = df.reset_index(drop=True)

        # cluster again with number of clusters set to 3, since we've extended the lap to 3 times the length
        n_clusters = len(df) / 3
        # round up to the nearest integer
        n_clusters = int(np.ceil(n_clusters))
        turns, labels = self.analyzer.cluster(
            [df], field="SpeedMs", n_clusters=n_clusters
        )
        turns = turns.sort_values(by=["DistanceRoundTrack"])
        turns = turns.reset_index(drop=True)

        track_info = []
        for i in range(len(turns)):
            # get the distance of the turn
            distance = turns["DistanceRoundTrack"].iloc[i]
            # get the speed of the turn
            speed = turns["SpeedMs"].iloc[i]

            if len(turns) == 1:
                start = (distance + max_distance / 2) % max_distance
                end = start
            else:
                if i == 0:
                    prev_distance = turns["DistanceRoundTrack"].iloc[len(turns) - 1]
                    next_distance = turns["DistanceRoundTrack"].iloc[i + 1]
                    d = distance + (max_distance - prev_distance)
                    start = (distance - d / 2) % max_distance
                    end = (distance + (next_distance - distance) / 2) % max_distance
                elif i == len(turns) - 1:
                    prev_distance = turns["DistanceRoundTrack"].iloc[i - 1]
                    next_distance = turns["DistanceRoundTrack"].iloc[0]
                    start = (distance - (distance - prev_distance) / 2) % max_distance
                    d = (max_distance - distance) + next_distance
                    end = (distance + d / 2) % max_distance
                else:
                    prev_distance = turns["DistanceRoundTrack"].iloc[i - 1]
                    next_distance = turns["DistanceRoundTrack"].iloc[i + 1]
                    start = (distance - (distance - prev_distance) / 2) % max_distance
                    end = (distance + (next_distance - distance) / 2) % max_distance

            # get the gear of the turn for each lap
            gears = []
            for df in laps:
                # get the gear of the turn
                # Create the boolean indexing mask
                min = (distance - 50) % max_distance
                max = (distance + 50) % max_distance
                if min > max:
                    tmp = min
                    min = max
                    max = tmp
                mask = (df["DistanceRoundTrack"] >= min) & (
                    df["DistanceRoundTrack"] <= max
                )
                # select all points in df where DistanceRoundTrack is between min and max
                gear = df.loc[mask]["Gear"].min()
                # print(gear)
                gears.append(gear)

            # find median gear
            # remove nan from gears
            gears = [x for x in gears if str(x) != "nan"]
            gear = int(np.median(gears))
            track_info.append(
                {
                    "start": start,
                    "end": end,
                    "brake": 0,
                    "force": 0,
                    "gear": gear,
                    "speed": speed,
                    "stop": 0,
                    "accelerate": distance,
                }
            )

        # convert track_info, which is an array of dict, to a pandas dataframe
        df = pd.DataFrame(track_info)
        logging.info(df.style.format(precision=1).to_string())
        return track_info
