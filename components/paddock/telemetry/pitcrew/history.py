#!/usr/bin/env python3

import threading
import os

# import pickle
import pandas as pd
import time
import logging
from telemetry.models import Game, FastLap, FastLapSegment, Driver
from telemetry.analyzer import Analyzer

from influxdb_client import InfluxDBClient

B4MAD_RACING_INFLUX_ORG = os.environ.get("B4MAD_RACING_INFLUX_ORG", "b4mad")
B4MAD_RACING_INFLUX_TOKEN = os.environ.get("B4MAD_RACING_INFLUX_TOKEN", "")
B4MAD_RACING_INFLUX_URL = os.environ.get(
    "B4MAD_RACING_INFLUX_URL", "https://telemetry.b4mad.racing/"
)


class History:
    def __init__(self):
        self.client = InfluxDBClient(
            url=B4MAD_RACING_INFLUX_URL,
            token=B4MAD_RACING_INFLUX_TOKEN,
            org=B4MAD_RACING_INFLUX_ORG,
        )
        self.pickle = False
        self.do_init = False
        self.segments = []
        self.segment_idx = 1
        self.previous_segment_idx = 0
        self.ready = False
        self.error = None
        self.do_run = True
        self.driver = None
        self.track_length = 0
        self.telemetry = pd.DataFrame()
        self.analyzer = Analyzer()

    def disconnect(self):
        self.do_run = False

    def run(self):
        while self.do_run:
            # TODO: rework time consuming stuff to be executed async
            time.sleep(5)
            if self.do_init:
                self.ready = self.init()
                self.do_init = False

    def set_filter(self, filter):
        self.filter = filter
        self.do_init = True

    def init(self):
        try:
            self.driver = Driver.objects.get(name=self.filter["Driver"])
            self.game = Game.objects.get(name=self.filter["GameName"])
            self.car = self.game.cars.get(name=self.filter["CarModel"])
            self.track = self.game.tracks.get(name=self.filter["TrackCode"])
            self.track_length = self.track.length
        except Exception as e:
            error = f"Error init {self.filter['Driver']} / {self.filter['GameName']}"
            error += f" / {self.filter['CarModel']}/  {self.filter['TrackCode']} - {e}"
            self.error = error
            logging.error(error)
            return False

        success = self.init_segments()
        if not success:
            return False

        self.init_driver()

        self.error = None
        self.telemetry_fields = [
            "DistanceRoundTrack",
            "Gear",
            "SpeedMs",
            "Throttle",
            "Brake",
            "CurrentLapTime",
        ]
        self.telemetry = {"_time": []}
        for field in self.telemetry_fields:
            self.telemetry[field] = []

        return True

    def init_driver(self):
        self.driver_segments = {}
        self.driver_data = {}
        fast_lap, created = FastLap.objects.get_or_create(
            car=self.car, track=self.track, game=self.game, driver=self.driver
        )
        # check if fast_lap has any fast_lap_segments
        if not FastLapSegment.objects.filter(fast_lap=fast_lap).exists():
            logging.debug(f"driver {self.driver} has no history for {fast_lap}")
            # initialize with segments from fast_lap
            for segment in self.segments:
                FastLapSegment.objects.create(fast_lap=fast_lap, turn=segment.turn)

        for segment in FastLapSegment.objects.filter(fast_lap=fast_lap):
            self.driver_segments[segment.turn] = segment
            self.driver_data[segment.turn] = {
                "gear": [],
                "brake": [],
            }

    # def write_cache_to_file(self):
    #     with open("cache.pickle", "wb") as outfile:
    #         pickle.dump(self.cache, outfile)

    # def read_cache_from_file(self):
    #     logging.debug("reading historic data from file")
    #     with open("cache.pickle", "rb") as infile:
    #         self.cache = pickle.load(infile)

    def in_range(self, meters, target, delta=10):
        start = target - delta
        end = target + delta

        if start < 0:
            start = self.track_length + start
            return meters <= end or meters >= start

        if end > self.track_length:
            end = end - self.track_length
            return meters <= end or meters >= start

        return start <= meters <= end

    def update(self, time, telemetry):
        self.telemetry["_time"].append(time)
        for field in self.telemetry_fields:
            self.telemetry[field].append(telemetry[field])

    def offset_distance(self, distance, seconds=0.0):
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
        return distance

    def t_segment(self, start, end):
        # FIXME: mod track length
        distance_round_track = self.telemetry["DistanceRoundTrack"]
        # go back until we have the first index where DistanceRoundTrack is between start and end
        idx = len(distance_round_track) - 1

        distance = distance_round_track[idx]

        # find the end index where DistanceRoundTrack is smaller than end
        while distance >= end and idx > 0:
            idx -= 1
            distance = distance_round_track[idx]
        end_idx = idx

        # find the start index where DistanceRoundTrack is smaller than start
        while distance >= start and idx > 0:
            idx -= 1
            distance = distance_round_track[idx]
        start_idx = idx

        if start_idx == end_idx:
            if start_idx > 0:
                start_idx -= 1
            else:
                end_idx += 1

        return start_idx, end_idx

    def t_start_idx(self, start, end, column="Brake"):
        start_idx, end_idx = self.t_segment(start, end)

        idx = start_idx
        while idx < end_idx:
            if self.telemetry[column][idx] > 0.001:
                return idx
            idx += 1
        return start_idx

    def t_start_distance(self, start, end, column="Brake"):
        idx = self.t_start_idx(start, end, column)
        return self.telemetry["DistanceRoundTrack"][idx]

    def t_at_distance(self, meters, column="SpeedMs"):
        start = meters - 1
        end = meters + 1
        start_idx, end_idx = self.t_segment(start, end)

        idx = end_idx
        distance = self.telemetry["DistanceRoundTrack"][idx]
        while distance > meters and idx > start_idx:
            idx -= 1
            distance = self.telemetry["DistanceRoundTrack"][idx]

        value = self.telemetry[column][idx]
        return value

    def driver_brake(self, segment):
        pass
        # driver_segment = self.driver_segments[segment.turn]
        # brake = self.driver_brake_start(segment.start - 50, segment.end)
        # if brake:
        #     self.driver_data[segment.turn]["brake"].append(brake)
        #     brake = statistics.median(self.driver_data[segment.turn]["brake"][-5:])
        #     driver_segment.brake = round(brake)
        #     driver_segment.save()
        # return driver_segment.brake

    def init_segments(self) -> bool:
        """Load the segments from DB."""
        fast_lap = FastLap.objects.filter(
            track=self.track, car=self.car, game=self.game
        ).first()
        if not fast_lap:
            self.error = f"no data found for game {self.filter['GameName']}"
            self.error += f"on track {self.filter['TrackCode']}"
            self.error += f"in car {self.filter['CarModel']}"
            logging.error(self.error)
            return False

        logging.debug(
            "loading segments for %s %s - %s", self.game, self.track, self.car
        )

        self.segments = []
        for segment in FastLapSegment.objects.filter(fast_lap=fast_lap).order_by(
            "turn"
        ):
            self.segments.append(segment)
            logging.debug("segment %s", segment)

        self.fast_lap = fast_lap

        logging.debug("loaded %s segments", len(self.segments))

        self.error = f"start coaching for game {self.filter['GameName']}"
        self.error += f"on track {self.filter['TrackCode']}"
        self.error += f"in car {self.filter['CarModel']}"
        return True


if __name__ == "__main__":
    filter = {
        "user": "durandom",
        "GameName": "iRacing",
        "TrackCode": "summit summit raceway",
        "CarModel": "Ferrari 488 GT3 Evo 2020",
    }
    history = History()
    history.set_filter(filter)

    threaded = True
    threaded = False

    if threaded:

        def history_thread():
            logging.info("History thread starting")
            history.run()

        x = threading.Thread(target=history_thread)
        x.start()
    else:
        history.init()
        logging.info(history.gear_q(100, 250))
