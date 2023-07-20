import logging
import statistics

from .analyzer import Analyzer
from .influx import Influx
from .models import FastLap
from .pitcrew.segment import Segment


class FastLapAnalyzer:
    def __init__(self, laps=[], bucket="fast_laps"):
        self.analyzer = Analyzer()
        self.laps = laps
        self.bucket = bucket
        self.influx_client = None
        self.same_sectors = False

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

    def current_fast_lap_sectors(self):
        lap = self.laps[0]
        car = lap.car
        track = lap.track
        game = lap.session.game
        fast_lap = FastLap.objects.filter(game=game, car=car, track=track, driver=None).first()
        sectors = []
        if fast_lap and fast_lap.data:
            for segment in fast_lap.data.get("segments", []):
                sectors.append(
                    {
                        "start": segment.start,
                        "end": segment.end,
                    }
                )
        return sectors

    def similar_sectors(self, sectors_a, sectors_b):
        if len(sectors_a) != len(sectors_b):
            return False

        if len(sectors_a) == 0:
            return False

        start_diffs = []
        for i in range(len(sectors_a)):
            start_diffs.append(abs(sectors_a[i]["start"] - sectors_b[i]["start"]))

        # med = statistics.median(start_diffs)
        med = statistics.mean(start_diffs)
        logging.debug(f"start_diffs: {start_diffs} med: {med}")
        if med > 40:
            return False

        return True

    def extract_sectors(self, lap_data):
        df_max = self.analyzer.combine_max_throttle(lap_data)
        sector_start_end = self.analyzer.split_sectors(
            df_max, min_distance_between_sectors=35, min_length_throttle_below_threshold=20
        )
        return sector_start_end, df_max

    def fastest_sector(self, data_frames, start, end):
        fast_sector = None
        fast_sector_time = 10_000_000_000_000
        fast_sector_idx = -1

        # logging.debug(f"start: {start}, end: {end}")
        for i, df in enumerate(data_frames):
            sector = self.analyzer.section_df(df, start, end)
            min_distance = sector["DistanceRoundTrack"].min()
            max_distance = sector["DistanceRoundTrack"].max()
            if start > end:
                tmp = start
                start = end
                end = tmp
            min_threshold = 10
            # be a bit more generous with the min_threshold if its the first sector
            # since those often dont start at 0
            if min_distance < 20:
                min_threshold = 20
            if abs(min_distance - start) > min_threshold:
                logging.debug(f"get sector for lap {i}: min: {min_distance} != start: {start}")
                continue
            if abs(max_distance - end) > 10:
                logging.debug(f"get sector for lap {i}: max: {max_distance} != end: {end}")
                continue
            # logging.debug(f"min_distance: {min_distance}, max_distance: {max_distance}")
            # continue if the sector is empty
            # check why this happens
            # pipenv run ./manage.py analyze \
            #   --game 'Automobilista 2' --track 'Snetterton:Snetterton_300' --car 'Ginetta G58'
            if sector.empty:
                logging.error(f"sector {i} is empty")
                continue

            # start_idx = -1
            # end_idx = 0
            # if start > end:
            #     logging.debug(f"sector {i} wrapped start: {start} > end: {end}")
            #     start_idx = 0
            #     end_idx = -1

            # sector_time = self.analyzer.sector_lap_time(sector)
            sector_time = self.analyzer.sector_time(sector)

            if sector_time < fast_sector_time:
                fast_sector = sector
                fast_sector_time = sector_time
                fast_sector_idx = i

        # logging.debug(f"fast_sector_idx: {fast_sector_idx} fast_sector_time: {fast_sector_time}")
        return fast_sector, fast_sector_idx

    def analyze(self, min_laps=1, max_laps=10):
        if not self.assert_can_analyze():
            logging.info("Can't analyze")
            return

        lap_telemetry, laps_with_telemetry = self.fetch_lap_telemetry(max_laps)

        if len(lap_telemetry) < min_laps:
            logging.info(f"Found {len(lap_telemetry)} laps, need {min_laps}")
            return

        sector_start_end, df_max = self.extract_sectors(lap_telemetry)

        current_sectors = self.current_fast_lap_sectors()
        if self.similar_sectors(sector_start_end, current_sectors):
            logging.info("Sectors are similar to current fast lap, using current fast lap")
            self.same_sectors = True
            sector_start_end = current_sectors

        segments, used_laps = self.extract_segments(sector_start_end, lap_telemetry, laps_with_telemetry, df_max)

        distance_time = self.analyzer.distance_speed_lookup_table(lap_telemetry[0])
        data = {
            "distance_time": distance_time,
            "segments": segments,
        }

        return data, list(used_laps)

    def extract_segments(self, sector_start_end, lap_telemetry, laps_with_telemetry, df_max):
        segments = []
        used_laps = set()
        track_length = df_max["DistanceRoundTrack"].max()
        for i in range(len(sector_start_end)):
            start = sector_start_end[i]["start"]
            end = sector_start_end[i]["end"]
            logging.debug(f"extract_segments for sector {i} start: {start} end: {end}")
            sector, lap_index = self.fastest_sector(lap_telemetry, start, end)
            if sector is None:
                logging.error(f"Could not find fastest sector for {start} - {end}")
                continue
            # merge Throttle input
            # sector['Throttle'] = df_max['Throttle']

            used_laps.add(laps_with_telemetry[lap_index])

            segment = self.extract_segment(sector)
            segment.start = start
            segment.end = end
            segment.turn = i + 1
            segment.track_length = track_length
            segment.time = self.analyzer.sector_lap_time(sector)
            segments.append(segment)
        return segments, used_laps

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
        other_features = {}

        segment = Segment()
        segment.type = throttle_or_brake

        if brake_features:
            segment.add_features(brake_features, type="brake")
        if throttle_features:
            segment.add_features(throttle_features, type="throttle")
        if gear_features:
            segment.add_features(gear_features, type="gear")
        if other_features:
            segment.add_features(other_features, type="other")

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
        df = df[df["Gear"] != 0].copy()
        # convert _time Timestamp column to int64
        df.loc[:, "Time"] = df["_time"].astype("int64")
        df = self.analyzer.resample(
            df,
            freq=1,
            columns=["Brake", "SpeedMs", "Throttle", "Gear", "CurrentLapTime", "SteeringAngle", "Time"],
        )
        return df
