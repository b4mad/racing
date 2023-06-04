import pandas as pd
import logging
from .influx import Influx
from .analyzer import Analyzer


class FastLapAnalyzer:
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

        distance_time = self.analyzer.distance_speed_lookup_table(df)
        data = {
            "distance_time": distance_time,
            "track_info": track_info,
        }
        return [track_info, data]

    def brake_features(self, df):
        brake_feature_args = {
            "brake_threshold": 0.1,
        }
        return self.analyzer.brake_features(df, **brake_feature_args)

    def throttle_features(self, df):
        throttle_features_args = {
            # "throttle_threshold": 0.98,
        }
        return self.analyzer.throttle_features(df, **throttle_features_args)

    def gear_features(self, df):
        gear = df["Gear"].min()
        return {
            "gear": gear,
        }

    def get_segments(self, track_df):
        analyzer = self.analyzer
        sectors = analyzer.split_sectors(track_df, min_length=50)
        sector_start_end = analyzer.extract_sector_start_end(sectors, min_length=50)
        sector_dfs = []
        track_info = []
        for i in range(len(sector_start_end)):
            sector = analyzer.section_df(track_df, sector_start_end[i]["start"], sector_start_end[i]["end"])
            sector_dfs.append(sector)

            throttle_or_brake = analyzer.sector_type(sector)

            brake_features = self.brake_features(sector)
            throttle_features = self.throttle_features(sector)
            gear_features = self.gear_features(sector)

            force = 0
            speed = 0
            if throttle_or_brake == "brake" and brake_features:
                force = brake_features["force"] * 100
                start = brake_features["start"]
                speed = analyzer.value_at_distance(sector, start, column="SpeedMs")
            elif throttle_or_brake == "throttle" and throttle_features:
                force = throttle_features["force"] * 100
                start = throttle_features["start"]
                speed = analyzer.value_at_distance(sector, start, column="SpeedMs")

            track_info.append(
                {
                    "mark": throttle_or_brake,
                    "start": sector_start_end[i]["start"],
                    "end": sector_start_end[i]["end"],
                    "gear": gear_features["gear"],
                    "force": force,
                    "speed": speed,
                    "brake_features": brake_features,
                    "throttle_features": throttle_features,
                    "gear_features": gear_features,
                    "df": sector,
                }
            )
        return track_info

    def preprocess(self, df):
        # # Check if the value is increasing compared to the previous value
        # is_increasing = df["DistanceRoundTrack"] > df["DistanceRoundTrack"].shift(1)

        # # Get the indices where the value is not increasing
        # not_increasing_indices = is_increasing[is_increasing == False].index.tolist()  # noqa: E712

        # if len(not_increasing_indices) > 1:
        #     logging.debug(f"Found {len(not_increasing_indices)} not increasing indices")

        # df = self.analyzer.drop_decreasing(df)
        # # dataframes with less than 100 points are not reliable
        # if len(df) < 100:
        #     logging.error(f"Dataframe has less than 100 points: {len(df)}")
        #     return
        df = df[df["Gear"] != 0]
        # display(df)
        df = self.analyzer.resample(
            df,
            freq=1,
            columns=["Brake", "SpeedMs", "Throttle", "Gear", "CurrentLapTime"],
        )
        return df
