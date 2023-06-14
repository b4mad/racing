import logging

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from .analyzer import Analyzer
from .influx import Influx


class FastLapAnalyzerV2:
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

        laps = self.influx.telemetry_for_laps(self.laps)
        if len(laps) == 0:
            return

        laps = self.analyzer.remove_uncorrelated_laps(laps, column="SpeedMs")
        # remove laps that are too different from the others
        laps = self.analyzer.remove_uncorrelated_laps(laps, column="Brake", threshold=0.5)

        if len(laps) == 0:
            return

        # get the max distance for each lap and select the max
        self.max_distance = np.max([df["DistanceRoundTrack"].max() for df in laps])

        cleaned_laps = []
        for df in laps:
            df = self.analyzer.drop_decreasing(df)
            # dataframes with less than 100 points are not reliable
            if len(df) < 100:
                continue
            df = self.analyzer.resample(df, columns=["Brake", "SpeedMs", "Gear", "CurrentLapTime"], freq=1)

            # smooth the laps
            window_length = 20  # meters
            if len(df) < window_length:
                # too short, skip
                logging.warning("lap too short, skipping")
                continue

            df = self.analyzer.extend_lap(df)

            df["Brake"] = savgol_filter(df["Brake"], window_length, 2)
            df["SpeedMs"] = savgol_filter(df["SpeedMs"], window_length, 2)
            cleaned_laps.append(df)

        gears_and_turns = self.get_gears_and_turns(cleaned_laps)
        brakepoints = self.get_brakepoints(cleaned_laps)

        # merge gears_and_turns and brakepoints based on the numeric value of the start key
        track_info = gears_and_turns + brakepoints
        track_info = sorted(track_info, key=lambda k: k["start"])

        # convert track_info, which is an array of dict, to a pandas dataframe
        df = pd.DataFrame(track_info)
        logging.info(df.style.format(precision=1).to_string())
        return track_info

    def get_brakepoints(self, laps):
        all_minima = []
        max_distance = self.max_distance
        track_info = []

        laps_with_extrema = []
        for df in laps:
            extrema = self.analyzer.local_maxima(df, column="Brake", points=50)
            logging.debug(f"number of maxima {len(extrema)} for lap {df['id'].iloc[0]}")
            if len(extrema) > 0:
                all_minima.append(extrema)
                laps_with_extrema.append(df)

        laps = laps_with_extrema

        if len(all_minima) == 0:
            return track_info

        centroids_df, labels = self.analyzer.cluster(all_minima, field="Brake")
        centroids_df = centroids_df.sort_values(by=["DistanceRoundTrack"])
        centroids_df = centroids_df.reset_index(drop=True)
        df = centroids_df.copy()

        # apply modulo length to DistanceRoundTrack
        df["DistanceRoundTrack"] = df["DistanceRoundTrack"].mod(max_distance)

        # sort the centroids by DistanceRoundTrack and reset the index
        df = df.sort_values(by=["DistanceRoundTrack"])
        df = df.reset_index(drop=True)

        # cluster again with number of clusters set to 3, since we've extended the lap to 3 times the length
        # round up to the nearest integer
        n_clusters = int(np.ceil(len(df) / 3))
        turns, labels = self.analyzer.cluster([df], field="Brake", n_clusters=n_clusters)
        turns = turns.sort_values(by=["DistanceRoundTrack"])
        turns = turns.reset_index(drop=True)

        for i in range(len(turns)):
            # get the distance of the turn
            brake_max = turns["Brake"].iloc[i]
            distance = turns["DistanceRoundTrack"].iloc[i]
            # display(f'brake force {brake_max} at distance {distance}')

            brake_starts = []
            brake_starts_minus_5 = []
            for df in laps:
                # go back from the turn to find where Brake starts
                brake = brake_max
                # find the index in df where DistanceRoundTrack is equal to distance
                if len(df[df["DistanceRoundTrack"] > distance]) > 0:
                    index = df[df["DistanceRoundTrack"] > distance].index[0]
                    brake_start = distance
                    while brake > 0.1:
                        index -= 1
                        if index < 0:
                            index = len(df) - 1
                        brake = df["Brake"].iloc[index]
                    brake_start = df["DistanceRoundTrack"].iloc[index]
                    brake_starts.append(brake_start)

                    # now go back 5.3 seconds
                    # because we'll read "Brake in 3 2 1", which take 5.3 seconds
                    current_lap_time = df["CurrentLapTime"].iloc[index]
                    target_lap_time = current_lap_time - 5.3
                    if target_lap_time < 0:
                        index = len(df) - 1
                        target_lap_time = df["CurrentLapTime"].max() - target_lap_time
                        current_lap_time = df["CurrentLapTime"].iloc[index]

                    cycles = 0
                    while current_lap_time > target_lap_time and cycles <= 2:
                        index -= 1
                        if index < 0:
                            index = len(df) - 1
                            cycles += 1
                        current_lap_time = df["CurrentLapTime"].iloc[index]

                    if cycles != 2:
                        brake_start_minus_5 = df["DistanceRoundTrack"].iloc[index]
                        brake_starts_minus_5.append(brake_start_minus_5)

            # find median gear
            brake_start = int(np.median(brake_starts))
            brake_start_minus_5 = int(np.median(brake_starts_minus_5))

            track_info.append(
                {
                    "start": brake_start_minus_5,
                    "brake": brake_start,
                    "force": brake_max,
                }
            )

        # df = pd.DataFrame(track_info)
        # logging.info(df.style.format(precision=1).to_string())
        return track_info

    def get_gears_and_turns(self, laps):
        all_minima = []
        max_distance = self.max_distance
        track_info = []

        laps_with_extrema = []
        for df in laps:
            minima = self.analyzer.local_minima(df, column="SpeedMs")
            logging.debug(f"number of minima {len(minima)} for lap {df['id'].iloc[0]}")
            if len(minima) > 0:
                laps_with_extrema.append(df)
                all_minima.append(minima)

        laps = laps_with_extrema
        if len(all_minima) == 0:
            return track_info

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
        # round up to the nearest integer
        n_clusters = int(np.ceil(len(df) / 3))
        turns, labels = self.analyzer.cluster([df], field="SpeedMs", n_clusters=n_clusters)
        turns = turns.sort_values(by=["DistanceRoundTrack"])
        turns = turns.reset_index(drop=True)

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
                mask = (df["DistanceRoundTrack"] >= min) & (df["DistanceRoundTrack"] <= max)
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
                    "gear": gear,
                    "speed": speed,
                    "accelerate": distance,
                }
            )

        # convert track_info, which is an array of dict, to a pandas dataframe
        # df = pd.DataFrame(track_info)
        # logging.info(df.style.format(precision=1).to_string())
        return track_info
