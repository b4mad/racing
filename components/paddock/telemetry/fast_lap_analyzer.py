import logging

from .analyzer import Analyzer
from .influx import Influx
from .pitcrew.segment import Segment


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
        # maybe check for game type
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

            analysis_dict = self.analyze_df(df)
            if analysis_dict:
                # append laps used for analysis
                return analysis_dict, [lap]

    def analyze_df(self, df):
        df = self.preprocess(df)
        if df is None:
            return

        segments = self.get_segments(df)
        # logging.info(track_info_df.style.format(precision=1).to_string())

        distance_time = self.analyzer.distance_speed_lookup_table(df)
        data = {
            "distance_time": distance_time,
            "segments": segments,
        }
        return data

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
        track_info = []
        for i in range(len(sector_start_end)):
            sector = analyzer.section_df(track_df, sector_start_end[i]["start"], sector_start_end[i]["end"])

            throttle_or_brake = analyzer.sector_type(sector)
            brake_features = self.brake_features(sector)
            throttle_features = self.throttle_features(sector)
            gear_features = self.gear_features(sector)

            segment = Segment()
            segment.type = throttle_or_brake
            segment.turn = i + 1

            speed = 0
            if throttle_or_brake == "brake" and brake_features:
                start = brake_features["start"]
                speed = analyzer.value_at_distance(sector, start, column="SpeedMs")
                brake_features["speed"] = speed
            elif throttle_or_brake == "throttle" and throttle_features:
                start = throttle_features["start"]
                speed = analyzer.value_at_distance(sector, start, column="SpeedMs")

            if brake_features:
                segment.add_features(brake_features, type="brake")
            if throttle_features:
                segment.add_features(throttle_features, type="throttle")
            if gear_features:
                segment.add_features(gear_features, type="gear")
            segment.telemetry = sector
            segment.start = sector_start_end[i]["start"]
            segment.end = sector_start_end[i]["end"]

            track_info.append(segment)
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
            columns=["Brake", "SpeedMs", "Throttle", "Gear", "CurrentLapTime", "SteeringAngle"],
        )
        return df
