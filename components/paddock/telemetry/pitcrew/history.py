#!/usr/bin/env python3

import statistics
import threading
import os

# import pickle
import pandas as pd
import numpy as np
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
            time.sleep(5)
            if self.do_init:
                self.ready = self.init()
                if self.ready:
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
        self.telemetry = pd.DataFrame(
            [
                {
                    "_time": time.time(),
                    "DistanceRoundTrack": 0,
                    "Gear": 0,
                    "SpeedMs": 0,
                    "Throttle": 0,
                    "Brake": 0,
                }
            ]
        )

        return True

    def init_driver(self):
        self.driver_segments = {}
        self.driver_data = {}
        fast_lap, created = FastLap.objects.get_or_create(
            car=self.car, track=self.track, game=self.game, driver=self.driver
        )
        # check if fast_lap has any fast_lap_segments
        if not FastLapSegment.objects.filter(fast_lap=fast_lap).exists():
            logging.error("no history found for %s", fast_lap)
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
        # add telemetry['Gear'] to dataframe
        t = pd.DataFrame(
            [
                {
                    "_time": time,
                    "DistanceRoundTrack": telemetry["DistanceRoundTrack"],
                    "Gear": telemetry["Gear"],
                    "SpeedMs": telemetry["SpeedMs"],
                    "Throttle": telemetry["Throttle"],
                    "Brake": telemetry["Brake"],
                }
            ]
        )

        self.telemetry = pd.concat([self.telemetry, t])
        # logging.debug("telemetry: %s", self.telemetry)

    def telemetry_segment(self, start, end):
        # FIXME: mod track length
        df = self.telemetry
        # go back until we have the first index where DistanceRoundTrack is between start and end
        idx = len(df) - 1

        end_idx = -1
        distance = df.iloc[idx]["DistanceRoundTrack"]
        while distance >= start and idx > 0:
            if distance <= end and end_idx == -1:
                end_idx = idx

            idx -= 1
            distance = df.iloc[idx]["DistanceRoundTrack"]

        start_idx = idx

        return df.iloc[start_idx:end_idx]
        # df = df[df["DistanceRoundTrack"].between(start, end)]

    def driver_gear(self, segment):
        driver_segment = self.driver_segments[segment.turn]
        df = self.telemetry_segment(segment.start, segment.end)

        gear = df[df["Gear"] > 0]["Gear"].min()

        if not np.isnan(gear):
            logging.debug("gear: %s", gear)

            self.driver_data[segment.turn]["gear"].append(gear)
            gear = statistics.median(self.driver_data[segment.turn]["gear"][-5:])
            driver_segment.gear = round(gear)
            driver_segment.save()

        # logging.debug("driver gear %s", driver_segment.gear)
        return driver_segment.gear

    def driver_brake_start(self, start, end):
        df = self.telemetry_segment(start, end)

        # find the DistanceRoundTrack where Brake is > 0.1
        brake = df[df["Brake"] > 0.1]["DistanceRoundTrack"].min()

        if not np.isnan(brake):
            return brake

        return None

    def driver_speed_at(self, meters):
        start = meters - 2
        end = meters + 2
        df = self.telemetry_segment(start, end)

        speed = df["SpeedMs"].mean()

        if not np.isnan(speed):
            return speed

        return 0

    def driver_brake(self, segment):
        driver_segment = self.driver_segments[segment.turn]
        brake = self.driver_brake_start(segment.start, segment.end + 200)
        if brake:
            self.driver_data[segment.turn]["brake"].append(brake)
            brake = statistics.median(self.driver_data[segment.turn]["brake"][-5:])
            driver_segment.brake = round(brake)
            driver_segment.save()
        return driver_segment.brake

    # def segment(self, meters: int, idx=None, depth=0) -> FastLapSegment:
    #     if len(self.segments) == 0:
    #         return None
    #     # stop the recursion if we are too deep
    #     if depth > len(self.segments):
    #         return None

    #     if idx is None:
    #         idx = self.segment_idx

    #     if idx >= len(self.segments):
    #         idx = 0

    #     segment = self.segments[idx]

    #     # check if meters is between .start and .end
    #     if segment.start <= meters < segment.end:
    #         self.segment_idx = idx
    #         return segment

    #     return self.segment(meters, idx=idx + 1, depth=depth + 1)

    def init_segments(self) -> bool:
        """Load the segments from DB."""
        fast_lap = FastLap.objects.filter(
            track=self.track, car=self.car, game=self.game
        ).first()
        if not fast_lap:
            self.error = f"no data found for game {self.filter['GameName']}"
            self.error += f"on track {self.filter['TrackCode']}"
            self.error += f"in car {self.filter['CarModel']}"
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
