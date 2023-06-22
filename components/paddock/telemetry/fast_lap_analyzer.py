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

    def fetch_lap_telemetry(self, max_laps=None):
        laps_with_telemetry = []
        lap_telemetry = []
        counter = 0
        for lap in self.laps:
            laps = self.influx().telemetry_for_laps([lap], measurement="fast_laps", bucket=self.bucket)
            if len(laps) == 0:
                logging.info("No data found for lap in fast_laps bucket, trying in default bucket")
                laps = self.influx().telemetry_for_laps([lap])
                if len(laps) == 0:
                    logging.info("No data found for lap, continuing")
                    continue
            laps_with_telemetry.append(lap)
            df = self.preprocess(laps[0])
            lap_telemetry.append(df)
            counter += 1
            if max_laps and counter >= max_laps:
                break

        return lap_telemetry, laps_with_telemetry

    def extract_sectors(self, lap_data):
        df_max = self.analyzer.combine_max_throttle(lap_data)
        sectors = self.analyzer.split_sectors(df_max)
        sector_start_end = self.analyzer.extract_sector_start_end(sectors)
        return sector_start_end

    def fastest_sector(self, data_frames, start, end):
        fast_sector = None
        fast_sector_time = 10_000_000_000_000
        fast_sector_idx = -1

        for i, df in enumerate(data_frames):
            sector = self.analyzer.section_df(df, start, end)

            if start < end:
                start_idx = -1
                end_idx = 0
            else:
                start_idx = 0
                end_idx = -1

            section_time = sector.iloc[start_idx]["Time"] - sector.iloc[end_idx]["Time"]

            if section_time < fast_sector_time:
                fast_sector = sector
                fast_sector_time = section_time
                fast_sector_idx = i

        # print(fast_sector_idx)
        return fast_sector, fast_sector_idx

    def analyze(self, min_laps=1, max_laps=10):
        if not self.assert_can_analyze():
            logging.info("Can't analyze")
            return

        lap_telemetry, laps_with_telemetry = self.fetch_lap_telemetry(max_laps)

        if len(lap_telemetry) < min_laps:
            logging.info(f"Found {len(lap_telemetry)} laps, need {min_laps}")
            return

        sector_start_end = self.extract_sectors(lap_telemetry)
        segments = []
        used_laps = set()
        for i in range(len(sector_start_end)):
            start = sector_start_end[i]["start"]
            end = sector_start_end[i]["end"]
            sector, lap_index = self.fastest_sector(lap_telemetry, start, end)
            used_laps.add(laps_with_telemetry[lap_index])

            segment = self.extract_segment(sector)
            segment.start = start
            segment.end = end
            segment.turn = i + 1
            segments.append(segment)

        distance_time = self.analyzer.distance_speed_lookup_table(lap_telemetry[0])
        data = {
            "distance_time": distance_time,
            "segments": segments,
        }

        return data, list(used_laps)

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

    def extract_segment(self, sector):
        analyzer = self.analyzer
        throttle_or_brake = analyzer.sector_type(sector)
        brake_features = self.brake_features(sector)
        throttle_features = self.throttle_features(sector)
        gear_features = self.gear_features(sector)

        segment = Segment()
        segment.type = throttle_or_brake

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
        return segment

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
        # convert _time Timestamp column to int64
        df["Time"] = df["_time"].astype("int64")
        df = self.analyzer.resample(
            df,
            freq=1,
            columns=["Brake", "SpeedMs", "Throttle", "Gear", "CurrentLapTime", "SteeringAngle", "Time"],
        )
        return df
