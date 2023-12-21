import time

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from telemetry.analyzer import Analyzer
from telemetry.fast_lap_analyzer import FastLapAnalyzer
from telemetry.models import Coach, Driver, FastLap, Game
from telemetry.pitcrew.logging_mixin import LoggingMixin
from telemetry.pitcrew.segment import Segment
from telemetry.racing_stats import RacingStats


class History(LoggingMixin):
    def __init__(self):
        self._do_init = False
        self.segments = []
        self.previous_update_meters = 0
        self._ready = False
        self._error = None
        self.do_run = True
        self.driver = None
        self.track_length = 0
        self.telemetry = []
        self.analyzer = Analyzer()
        self.fast_lap_analyzer = FastLapAnalyzer()
        self.racing_stats = RacingStats()
        self.fast_lap = None
        self.process_segments = []
        self.threaded = False
        self.session_id = "NO_SESSION"
        self.coach_mode = Coach.MODE_DEFAULT

    def disconnect(self):
        self.do_run = False

    def run(self):
        self.threaded = True
        while self.do_run:
            time.sleep(0.1)
            if self._ready:
                self.do_work()
            if self._do_init:
                self.init()
                self._do_init = False

    def set_filter(self, filter, coach_mode=Coach.MODE_DEFAULT):
        self._ready = False
        self.filter = filter
        self.session_id = filter.get("SessionId", "NO_SESSION")
        self.coach_mode = coach_mode
        self._do_init = True

    def set_coach_mode(self, coach_mode):
        self.coach_mode = coach_mode

    def is_initializing(self):
        return self._do_init

    def is_ready(self):
        return self._ready

    def get_and_reset_error(self):
        if self._error:
            error = self._error
            self._error = None
            return error

    def init(self):
        self._ready = False
        self._error = None
        self.process_segments = []
        self.telemetry = []

        try:
            self.driver = Driver.objects.get(name=self.filter["Driver"])
            self.game = Game.objects.get(name=self.filter["GameName"])
            self.car = self.game.cars.get(name=self.filter["CarModel"])
            self.track = self.game.tracks.get(name=self.filter["TrackCode"])
            self.track_length = self.track.length
        except Exception as e:
            error = f"Error init {self.filter['Driver']} / {self.filter['GameName']}"
            error += f" / {self.filter['CarModel']}/  {self.filter['TrackCode']} - {e}"
            self._error = error
            self.log_error(error)
            return False

        if self.init_segments():
            if self.init_driver():
                self._ready = True
                return True

    def init_segments(self) -> bool:
        """Load the segments from DB."""
        fast_lap = FastLap.objects.filter(track=self.track, car=self.car, game=self.game).first()
        if not fast_lap or not fast_lap.data or not fast_lap.data.get("segments"):
            error = f"no data found for game {self.filter['GameName']}"
            error += f" on track {self.filter['TrackCode']}"
            error += f" in car {self.filter['CarModel']}"
            self._error = error
            self.log_error(error)
            return False

        self.log_debug("loading segments for %s %s - %s", self.game, self.track, self.car)
        self.log_debug(f"  based on laps {fast_lap.laps.count()}")

        self.segments = fast_lap.data.get("segments")

        for i, segment in enumerate(self.segments):
            next_index = (i + 1) % len(self.segments)
            previous_index = (i - 1) % len(self.segments)
            segment.previous_segment = self.segments[previous_index]
            segment.next_segment = self.segments[next_index]
            segment.history = self

        self.fast_lap = fast_lap

        self.build_lookup_tables()

        # self.log_debug("loaded %s segments", len(self.segments))
        return True

    def init_driver(self):
        self.driver_fast_lap, created = FastLap.objects.get_or_create(
            car=self.car, track=self.track, game=self.game, driver=self.driver
        )

        driver_data = self.driver_fast_lap.data
        if not driver_data:
            segments = {}
            for segment in self.segments:
                driver_segment = Segment()
                driver_segment.copy_from(segment)
                segments[segment.turn] = driver_segment
            driver_data = {
                "segments": segments,
            }
            self.log_debug("no driver data found")
            self.driver_fast_lap.data = driver_data

        driver_segments = self.driver_fast_lap.data.get("segments", {})
        empty_segment = Segment()
        for segment in self.segments:
            driver_segment = driver_segments.get(segment.turn, empty_segment)
            if self.coach_mode != Coach.MODE_TRACK_GUIDE:
                segment.init_live_features_from_segment(driver_segment)

        return True

    def update(self, time, telemetry):
        meters = int(telemetry["DistanceRoundTrack"])
        if meters != self.previous_update_meters:
            data = telemetry
            data["_time"] = time
            return self.update_telemetry(meters, data)

    def update_telemetry(self, meters, data, depth=0):
        if depth > len(self.segments):
            self.log_debug(f"update_telemetry: meters: {meters} no segment found")
            return

        segment = self.segments[0]
        start = segment.start
        end = segment.end

        if start < end:
            in_segment = start <= meters <= end
        else:
            in_segment = meters >= start or meters <= end

        if in_segment:
            self.telemetry.append(data)
            self.previous_update_meters = meters
        else:
            work_to_do = False
            if len(self.telemetry) > 0:
                segment.live_telemetry.append(self.telemetry)
                self.process_segments.append(segment)
                self.telemetry = []
                work_to_do = True

            self.segments.append(self.segments.pop(0))
            self.update_telemetry(meters, data, depth + 1)
            return work_to_do

    def do_work(self):
        # self.log_debug(f"do work")
        while len(self.process_segments) > 0:
            segment = self.process_segments.pop(0)
            log_prefix = f"processing segment {segment.turn} "
            if len(segment.live_telemetry) == 0:
                self.log_error(f"{log_prefix} no telemetry for segment")
                continue

            telemetry = segment.live_telemetry.pop(0)
            if len(telemetry) == 0:
                self.log_error(f"{log_prefix} no data in telemetry")
                continue

            # lap_number = telemetry[0].get("CurrentLap")
            # self.log_debug(f"   lap: {lap_number}")

            df = pd.DataFrame.from_records(telemetry)
            df = self.fast_lap_analyzer.preprocess(df)

            brake_features = self.fast_lap_analyzer.brake_features(df)
            throttle_features = self.fast_lap_analyzer.throttle_features(df)
            gear_features = self.fast_lap_analyzer.gear_features(df)
            sector_time = self.analyzer.sector_time(df)
            sector_lap_time = self.analyzer.sector_lap_time(df)
            other_features = {
                "sector_time": sector_time,
                "sector_lap_time": sector_lap_time,
            }

            segment.add_live_features(brake_features, type="brake")
            segment.add_live_features(throttle_features, type="throttle")
            segment.add_live_features(gear_features, type="gear")
            segment.add_live_features(other_features, type="other")

            # FIXME: this produces a lot of large updates in the database
            #        * refactor the DB design to store the data in a more efficient way
            #        * store the data in a document database like MongoDB
            driver_segment = self.driver_fast_lap.data["segments"][segment.turn]
            driver_segment.add_live_features(brake_features, type="brake")
            driver_segment.add_live_features(throttle_features, type="throttle")
            driver_segment.add_live_features(gear_features, type="gear")
            driver_segment.add_live_features(other_features, type="other")
            self.driver_fast_lap.save()

            segment.live_telemetry_frames.append(df)

            self.log_debug(f"{log_prefix} driver delta: {segment.driver_delta()}")

    def build_lookup_tables(self):
        """Build lookup tables for fast lap data."""
        df = self.fast_lap.data.get("distance_time")
        # df is a pandas dataframe with CurrentLapTime, SpeedMs and DistanceRoundTrack as columns
        # 1. round DistanceRoundTrack to integer
        # 2. create a dictionary with DistanceRoundTrack as key and SpeedMs as value

        min_distance = 0
        max_distance = self.track_length
        target_rows = max_distance + 1

        new_distance_round_track = np.linspace(min_distance, max_distance, target_rows)
        new_distance_round_track = np.round(new_distance_round_track, decimals=0).astype(int)

        resampled_df = pd.DataFrame({"DistanceRoundTrack": new_distance_round_track})

        for column in ["CurrentLapTime", "SpeedMs"]:
            interp = interp1d(
                df["DistanceRoundTrack"], df[column], kind="nearest", bounds_error=False, fill_value="extrapolate"
            )
            interpolated_values = interp(new_distance_round_track)

            if np.issubdtype(df[column].dtype, np.integer):
                interpolated_values = np.round(interpolated_values).astype(int)

            resampled_df[column] = interpolated_values

        df = resampled_df

        # Create dictionary with DistanceRoundTrack as key and SpeedMs as value
        self.map_distance_speed = dict(zip(df["DistanceRoundTrack"], df["SpeedMs"]))
        # Create dictionary with DistanceRoundTrack as key and CurrentLapTime as value
        self.map_distance_time = dict(zip(df["DistanceRoundTrack"], df["CurrentLapTime"]))
        # Create dictionary with CurrentLapTime as key and DistanceRoundTrack as value
        self.map_time_distance = dict(zip(df["CurrentLapTime"], df["DistanceRoundTrack"]))
        self.map_time_distance_max = max(self.map_time_distance.keys())

    def lap_time_at_distance(self, distance):
        lap_time = self.map_distance_time.get(distance, 0.0)
        if lap_time == 0.0:
            self.log_error(f"no lap_time at {distance} - map: {self.map_distance_time}")
        return lap_time

    def speed_at_distance(self, distance):
        speed = self.map_distance_speed.get(distance, 0.0)
        if speed == 0.0:
            self.log_error(f"no speed at {distance} - map: {self.map_distance_speed}")
        return speed

    def distance_at_lap_time(self, lap_time):
        distance = self.map_time_distance.get(lap_time, None)
        if distance is None:
            keys = self.map_time_distance.keys()
            # get the closest key
            # FIXME: this is probably too expensive, maybe have multiple lookup tables,
            #        with different resolutions, 3 decimals, 2 decimals, 1 decimal, integer
            closest_key = min(keys, key=lambda x: abs(x - lap_time))
            distance = self.map_time_distance[closest_key]
        return distance

    def distance_add(self, distance, meters):
        return (distance + meters) % self.track_length

    def distance_add_seconds(self, distance, seconds):
        time_at_distance = self.lap_time_at_distance(distance)
        target_time = (time_at_distance + seconds) % self.map_time_distance_max
        return self.distance_at_lap_time(target_time)

    def offset_distance(self, distance, seconds=0.0):
        self.log_debug(f"offset_distance from {distance} {seconds:.2f}")
        if self.fast_lap.data:
            distance_time = self.fast_lap.data.get("distance_time", {})
            # check if distance_time is a pandas dataframe
            if isinstance(distance_time, pd.DataFrame):
                # check if index at distance exists
                distance = round(distance)
                if distance < len(distance_time):
                    lap_time = distance_time.loc[distance]["CurrentLapTime"]
                    lap_time_at_offset = lap_time - seconds

                    if lap_time_at_offset < 0:
                        # FIXME wrap around and start counting back from the end of the track
                        return 0

                    # loop backwards until we find the first index where CurrentLapTime is smaller than offset
                    while lap_time > lap_time_at_offset and distance > 0:
                        distance -= 1
                        lap_time = distance_time.loc[distance]["CurrentLapTime"]
        self.log_debug(f"offset_distance   to {distance} {seconds:.2f}")
        return distance

    def lap_time(self):
        lap_time_seconds = 0.0
        for segment in self.segments:
            lap_time_seconds += segment.time
        return lap_time_seconds

    def lap_time_human(self, time_in_seconds=None):
        if time_in_seconds is None:
            time_in_seconds = self.lap_time()

        minutes = int(time_in_seconds // 60)
        seconds = round(time_in_seconds % 60, 2)
        # milliseconds = int((coach_lap_time % 1) * 1000)
        time_string = ""
        if minutes > 1:
            time_string += f"{minutes} minutes "
        elif minutes == 1:
            time_string += f"{minutes} minute "

        time_string += f"{seconds:.2f} seconds "

        return time_string

    def driver_opt_delta(self):
        # calculate driver delta for the whole lap
        delta = 0.0
        for segment in self.segments:
            segment_driver_delta = segment.driver_delta()
            self.log_debug(f"segment {segment.turn} driver delta: {segment_driver_delta}")
            delta += segment_driver_delta

        return delta

    def driver_delta(self):
        driver_laps = self.racing_stats.laps(
            game=self.game,
            track=self.track,
            car=self.car,
            driver=self.driver.name,
            valid=True,
        )

        try:
            lap = driver_laps[0]
        except IndexError:
            return -10000

        if lap:
            delta = lap.time - self.lap_time()
            return delta
        return -10000

    def driver_laps_count(self):
        driver_laps = self.racing_stats.laps(
            game=self.game,
            track=self.track,
            car=self.car,
            driver=self.driver.name,
            valid=True,
        )
        return driver_laps.count()

    def ranked_turns(self):
        ranked_turns = self.segments.copy()
        ranked_turns.sort(key=lambda x: x.driver_delta(), reverse=True)
        return ranked_turns
