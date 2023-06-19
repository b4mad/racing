import logging

import numpy as np
import pandas as pd

from .analyzer import Analyzer
from .influx import Influx


class FastLapAnalyzerV3:
    def __init__(self, laps=[], bucket="fast_laps"):
        self.analyzer = Analyzer()
        self.laps = laps
        self.bucket = bucket
        self.influx_client = None

    def influx(self):
        if not self.influx_client:
            self.influx_client = Influx()
        return self.influx_client

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
            logging.info("Can't analyze")
            return

        for lap in self.laps:
            laps = self.influx().telemetry_for_laps([lap], measurement="fast_laps", bucket=self.bucket)
            if len(laps) == 0:
                logging.info("No laps found")
                continue

            df = laps[0]

            result = self.analyze_df(df)
            if result:
                result.append([lap])
                return result

    def analyze_df(self, df):
        df = self.preprocess(df)
        if df is None:
            return

        segments = self.get_segments(df)
        track_info = sorted(segments, key=lambda k: k["start"])

        # convert track_info, which is an array of dict, to a pandas dataframe
        track_info_df = pd.DataFrame(track_info)
        logging.info(track_info_df.style.format(precision=1).to_string())

        distance_time = self.get_distance_time(df)
        data = {
            "distance_time": distance_time,
        }
        return [track_info, data]

    def preprocess(self, df):
        # Check if the value is increasing compared to the previous value
        is_increasing = df["DistanceRoundTrack"] > df["DistanceRoundTrack"].shift(1)

        # Get the indices where the value is not increasing
        not_increasing_indices = is_increasing[is_increasing == False].index.tolist()  # noqa: E712

        if len(not_increasing_indices) > 1:
            logging.info(f"Found {len(not_increasing_indices)} not increasing indices")

        df = self.analyzer.drop_decreasing(df)
        # dataframes with less than 100 points are not reliable
        if len(df) < 100:
            return
        df = df[df["Gear"] != 0]
        # display(df)
        df = self.analyzer.resample(
            df,
            freq=1,
            columns=["Brake", "SpeedMs", "Throttle", "Gear", "CurrentLapTime"],
        )
        return df

    def get_distance_time(self, lap):
        # find the index where the lap starts, thats where CurrentLapTime is minimal
        # only keep the part of the lap after the start
        lap = lap[["DistanceRoundTrack", "CurrentLapTime", "SpeedMs"]]
        lap = self.analyzer.resample(lap, freq=1, columns=["CurrentLapTime", "SpeedMs"])
        lap_start = lap["CurrentLapTime"].idxmin()

        # display(lap_start)

        # for all indices until lap_start, calculate a new value for CurrentLapTime
        # CurrentLapTime = DistanceRoundTrack * SpeedMs

        lap.loc[:lap_start, "CurrentLapTime"] = (
            lap.loc[:lap_start, "DistanceRoundTrack"] / lap.loc[:lap_start, "SpeedMs"]
        )
        # lap.loc[lap_start-10:lap_start+10]
        # remove id and SpeedMs column
        lap = lap[["DistanceRoundTrack", "CurrentLapTime"]]
        # round DistanceRoundTrack to 1 decimal
        lap["DistanceRoundTrack"] = lap["DistanceRoundTrack"].round(1)
        # round CurrentLapTime to 3 decimals
        lap["CurrentLapTime"] = lap["CurrentLapTime"].round(3)
        return lap

    def get_segments(self, df):
        throttle_changes = self.get_change_indices(df, "Throttle", threshold=0.95, below=True)
        brake_changes = self.get_change_indices(df, "Brake", threshold=0.005, below=False)

        throttle_changes = self.remove_close_indices(throttle_changes)
        brake_changes = self.remove_close_indices(brake_changes)

        segments = []
        for i in range(0, len(throttle_changes), 2):
            start_i = throttle_changes[i]
            end_i = throttle_changes[i + 1]
            # find the closest number in the brake_idx array

            if len(brake_changes):
                # how far is the brake_idx from the start_idx
                brake_i = brake_changes[np.abs(brake_changes - start_i).argmin()]
            else:
                # no brake changes
                brake_i = 999999

            distance = np.abs(brake_i - start_i)
            segment = {
                "type": "brake",
                "seg_start": start_i,
                "seg_end": end_i,
                "color": "yellow",
            }
            if distance > 20:
                # we are not braking in this segment
                segment["type"] = "throttle"
                segment["color"] = "green"
                segment["start"] = start_i
                segment["end"] = end_i
                segment["speed"] = df["SpeedMs"][start_i]

                avg_data = self.get_average(df, start_i, end_i, column="Throttle", max=False)
                if len(avg_data) == 0:
                    continue
                segment |= avg_data
            else:
                # search back 20 meters to find the start of the brake
                search_start = brake_i - 20
                if search_start < 0:
                    search_start = 0
                search_df = df[search_start:brake_i]
                if len(search_df) == 0:
                    continue
                min = search_df["Brake"].min()
                brake_start_i = search_df[search_df["Brake"] == min].index.max()
                segment["start"] = brake_start_i
                segment["speed"] = df["SpeedMs"][brake_start_i]

                search_df = df[brake_start_i:end_i]
                brake_end_i = search_df[search_df["Brake"] >= min].index.max()
                segment["end"] = brake_end_i

                # find the max brake value
                avg_data = self.get_average(df, brake_i, end_i)
                if len(avg_data) == 0:
                    continue
                segment |= avg_data

            # get lowest gear in this segment
            segment["gear"] = df["Gear"][segment["seg_start"] : segment["seg_end"]].min()
            segment["speed"] = df["SpeedMs"][segment["seg_start"] : segment["seg_end"]].min()
            segments.append(segment)

        track_info = []
        for segment in segments:
            track_info.append(
                {
                    "mark": segment["type"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "gear": segment["gear"],
                    "force": segment["average"] * 100,
                    "speed": segment["speed"],
                }
            )

        return track_info

    def get_average(self, df, start_i, end_i, column="Brake", max=True):
        search_df = df[start_i:end_i]
        if len(search_df) == 0:
            return {}

        if max:
            high = abs(round(search_df[column].max(), 2))
            low = high * 0.9
            start = search_df[search_df[column] > low].index.min()
            end = search_df[search_df[column] > low].index.max()
            average = search_df[search_df[column] > low][column].mean()
        else:
            low = abs(round(search_df[column].min(), 2))
            high = low * 1.1
            if low <= 0.1:
                high = 0.1
            start = search_df[search_df[column] < high].index.min()
            end = search_df[search_df[column] < high].index.max()
            average = search_df[search_df[column] < high][column].mean()

        if np.isnan(average):
            average = (high + low) / 2

        return {
            "high": high,
            "low": low,
            "avg_start": start,
            "avg_end": end,
            "average": round(average, 2),
        }

    def get_change_indices(self, df, column, threshold=0.9, below=True):
        x = df[column].values
        if below:
            mask = x <= threshold
        else:
            mask = x >= threshold
        change_indices = np.where(np.diff(mask))[0]
        # if len(change_indices) is odd, then the last value is a change
        if len(change_indices) % 2 == 1:
            print("adding last index")
            change_indices = np.append(change_indices, len(x) - 1)
        return change_indices

    def remove_close_indices(self, indices, threshold=50):
        if len(indices) == 0:
            return indices
        # merge throttle changes that are close together
        new_indices = [
            indices[0],
            indices[1],
        ]
        for i in range(2, len(indices), 2):
            start_i = indices[i]
            end_i = indices[i + 1]
            previous_end = indices[i - 1]
            if start_i - previous_end <= threshold:
                new_indices[-1] = end_i
            else:
                new_indices.append(start_i)
                new_indices.append(end_i)
        return new_indices
