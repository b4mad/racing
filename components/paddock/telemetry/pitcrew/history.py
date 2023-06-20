import time

import pandas as pd

from telemetry.analyzer import Analyzer
from telemetry.fast_lap_analyzer import FastLapAnalyzer
from telemetry.models import Driver, FastLap, Game
from telemetry.pitcrew.logging import LoggingMixin


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
        self.fast_lap = None
        self.process_segments = []
        self.threaded = False
        self.session_id = "NO_SESSION"

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

    def set_filter(self, filter):
        self._ready = False
        self.filter = filter
        self.session_id = filter.get("SessionId", "NO_SESSION")
        self._do_init = True

    def is_initializing(self):
        return self._do_init

    def is_ready(self):
        return self._ready

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
        if not fast_lap:
            error = f"no data found for game {self.filter['GameName']}"
            error += f" on track {self.filter['TrackCode']}"
            error += f" in car {self.filter['CarModel']}"
            self._error = error
            self.log_error(error)
            return False

        self.log_debug("loading segments for %s %s - %s", self.game, self.track, self.car)
        self.log_debug(f"  based on laps {fast_lap.laps}")
        # self.track_info = fast_lap.data.get("track_info", [])
        # self.log_debug(f"  track_info\n{self.track_info}")

        self.segments = fast_lap.data.get("segments", [])
        # for segment in FastLapSegment.objects.filter(fast_lap=fast_lap).order_by("turn"):
        #     s = Segment(self, **model_to_dict(segment))
        #     s["brake_features"] = self.features(s, mark="brake")
        #     s["throttle_features"] = self.features(s, mark="throttle")
        #     s["telemetry"] = []
        #     s["telemetry_frames"] = []
        #     self.segments.append(s)
        #     self.log_debug("segment %s", segment)

        # self.segments = self.sort_segments()

        for segment in self.segments:
            segment.history = self

        self.fast_lap = fast_lap

        # self.log_debug("loaded %s segments", len(self.segments))
        return True

    def get_and_reset_error(self):
        if self._error:
            error = self._error
            self._error = None
            return error

    def features(self, segment, mark="brake"):
        # search through segements
        for item in self.track_info:
            if item["mark"] == mark:
                if item["start"] == segment["start"]:
                    return item[f"{mark}_features"]
        return {}

    def sort_segments(self, distance=0):
        segments = sorted(self.segments, key=lambda k: k["start"])
        index_of_first_item = 0

        # loop through messages and find index of first item larger than distance
        for i, segment in enumerate(segments):
            index_of_first_item = i
            if segment["start"] >= distance > segment["end"]:
                break

        return segments[index_of_first_item:] + segments[:index_of_first_item]

    def init_driver(self):
        self.driver_segments = {}
        self.driver_data = {}
        return True
        # fast_lap, created = FastLap.objects.get_or_create(
        #     car=self.car, track=self.track, game=self.game, driver=self.driver
        # )
        # # check if fast_lap has any fast_lap_segments
        # if not FastLapSegment.objects.filter(fast_lap=fast_lap).exists():
        #     self.log_debug(f"driver {self.driver} has no history for {fast_lap}")
        #     # initialize with segments from fast_lap
        #     for segment in self.segments:
        #         FastLapSegment.objects.create(fast_lap=fast_lap, turn=segment["turn"])

        # for segment in FastLapSegment.objects.filter(fast_lap=fast_lap):
        #     self.driver_segments[segment.turn] = segment
        #     self.driver_data[segment.turn] = {
        #         "gear": [],
        #         "brake": [],
        #     }

    def update(self, time, telemetry):
        meters = int(telemetry["DistanceRoundTrack"])
        if meters != self.previous_update_meters:
            data = telemetry
            data["_time"] = time
            return self.update_telemetry(meters, data)

    def update_telemetry(self, meters, data, depth=0):
        if depth > len(self.segments):
            self.log_error(f"update_telemetry: meters: {meters} no segment found")
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

            segment.add_live_features(brake_features, type="brake")
            segment.add_live_features(throttle_features, type="throttle")
            segment.add_live_features(gear_features, type="gear")

            segment.live_telemetry_frames.append(df)

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

    # def in_range(self, meters, target, delta=10):
    #     start = target - delta
    #     end = target + delta

    #     if start < 0:
    #         start = self.track_length + start
    #         return meters <= end or meters >= start

    #     if end > self.track_length:
    #         end = end - self.track_length
    #         return meters <= end or meters >= start

    #     return start <= meters <= end
    # def t_segment(self, start, end):
    #     # FIXME: mod track length
    #     distance_round_track = self.telemetry["DistanceRoundTrack"]
    #     # go back until we have the first index where DistanceRoundTrack is between start and end
    #     idx = len(distance_round_track) - 1

    #     distance = distance_round_track[idx]

    #     # find the end index where DistanceRoundTrack is smaller than end
    #     while distance >= end and idx > 0:
    #         idx -= 1
    #         distance = distance_round_track[idx]
    #     end_idx = idx

    #     # find the start index where DistanceRoundTrack is smaller than start
    #     while distance >= start and idx > 0:
    #         idx -= 1
    #         distance = distance_round_track[idx]
    #     start_idx = idx

    #     if start_idx == end_idx:
    #         if start_idx > 0:
    #             start_idx -= 1
    #         else:
    #             end_idx += 1

    #     return start_idx, end_idx

    # def t_start_idx(self, start, end, column="Brake"):
    #     start_idx, end_idx = self.t_segment(start, end)

    #     idx = start_idx
    #     while idx < end_idx:
    #         if self.telemetry[column][idx] > 0.001:
    #             return idx
    #         idx += 1
    #     return start_idx

    # def t_start_distance(self, start, end, column="Brake"):
    #     idx = self.t_start_idx(start, end, column)
    #     return self.telemetry["DistanceRoundTrack"][idx]

    # def t_at_distance(self, meters, column="SpeedMs"):
    #     start = meters - 1
    #     end = meters + 1
    #     start_idx, end_idx = self.t_segment(start, end)

    #     idx = end_idx
    #     distance = self.telemetry["DistanceRoundTrack"][idx]
    #     while distance > meters and idx > start_idx:
    #         idx -= 1
    #         distance = self.telemetry["DistanceRoundTrack"][idx]

    #     value = self.telemetry[column][idx]
    #     return value

    # def driver_brake(self, segment):
    #     pass
    #     # driver_segment = self.driver_segments[segment.turn]
    #     # brake = self.driver_brake_start(segment.start - 50, segment.end)
    #     # if brake:
    #     #     self.driver_data[segment.turn]["brake"].append(brake)
    #     #     brake = statistics.median(self.driver_data[segment.turn]["brake"][-5:])
    #     #     driver_segment.brake = round(brake)
    #     #     driver_segment.save()
    #     # return driver_segment.brake
