#!/usr/bin/env python3

import threading
import os
import pickle
import time
import logging
from telemetry.models import Game, Car, Track, FastLap, FastLapSegment, Driver

from influxdb_client import InfluxDBClient

_LOGGER = logging.getLogger(__name__)

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

    def disconnect(self):
        self.do_run = False

    def run(self):
        while self.do_run:
            time.sleep(1)
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
            self.car = Car.objects.get(name=self.filter["CarModel"])
            self.game = Game.objects.get(name=self.filter["GameName"])
            self.track = Track.objects.get(name=self.filter["TrackCode"])
        except Exception as e:
            _LOGGER.error(e)
            return False

        success = self.init_segments()
        if not success:
            return False

        if self.pickle:
            self.read_cache_from_file()
        else:
            self.init_cache()

        self.error = None
        return True

    def init_cache(self):
        self.cache = {}
        fast_lap, created = FastLap.objects.get_or_create(
            car=self.car, track=self.track, game=self.game, driver=self.driver
        )
        # check if fast_lap has any fast_lap_segments
        if not FastLapSegment.objects.filter(fast_lap=fast_lap).exists():
            _LOGGER.error("no history found for %s", fast_lap)
            # initialize with segments from fast_lap
            for segment in self.segments:
                FastLapSegment.objects.create(fast_lap=fast_lap, turn=segment.turn)

        for segment in FastLapSegment.objects.filter(fast_lap=fast_lap):
            self.cache[segment.turn] = segment

    def write_cache_to_file(self):
        with open("cache.pickle", "wb") as outfile:
            pickle.dump(self.cache, outfile)

    def read_cache_from_file(self):
        _LOGGER.debug("reading historic data from file")
        with open("cache.pickle", "rb") as infile:
            self.cache = pickle.load(infile)

    def segment(self, meters: int, idx=None, depth=0) -> FastLapSegment:
        if len(self.segments) == 0:
            return None
        # stop the recursion if we are too deep
        if depth > len(self.segments):
            return None

        if idx is None:
            idx = self.segment_idx

        if idx >= len(self.segments):
            idx = 0

        segment = self.segments[idx]

        # check if meters is between .start and .end
        if segment.start <= meters < segment.end:
            self.segment_idx = idx
            return segment

        return self.segment(meters, idx=idx + 1, depth=depth + 1)

    def init_segments(self) -> bool:
        """Load the segments from DB."""
        game = Game.objects.filter(name=self.filter["GameName"]).first()
        if not game:
            self.error = f"Game {self.filter['GameName']} not found"
            _LOGGER.error(self.error)
            return False

        track = Track.objects.filter(game=game, name=self.filter["TrackCode"]).first()
        if not game:
            self.error = f"no data found for {self.filter['GameName']} {self.filter['TrackCode']}"
            _LOGGER.error(self.error)
            return False

        car = Car.objects.filter(game=game, name=self.filter["CarModel"]).first()
        if not car:
            self.error = (
                f"no data found for {self.filter['GameName']} {self.filter['TrackCode']}"
                + f"- {self.filter['CarModel']}"
            )
            _LOGGER.error(self.error)
            return False

        fast_lap = FastLap.objects.filter(track=track, car=car, game=game).first()
        if not fast_lap:
            self.error = (
                f"no data found for {self.filter['GameName']} {self.filter['TrackCode']}"
                + f"- {self.filter['CarModel']}"
            )
            _LOGGER.error(self.error)
            return False

        _LOGGER.debug("loading segments for %s %s - %s", game, track, car)

        self.segments = []
        for segment in FastLapSegment.objects.filter(fast_lap=fast_lap).order_by(
            "turn"
        ):
            self.segments.append(segment)

        _LOGGER.debug("loaded %s segments", len(self.segments))

        self.error = (
            f"start coaching for {self.filter['GameName']} {self.filter['TrackCode']}"
            + f"- {self.filter['CarModel']}"
        )
        return True

    def gear(self, segment):
        return self.cache[segment.turn].gear

    def off_gear(self, brakepoint):
        return self.cache["gear"].get(brakepoint["corner"])

    def off_gear_q(self, start, stop):
        vars = self.filter.copy()
        vars.update({"start": start - 20, "stop": stop})
        q = """
        from(bucket: "racing")
          |> range(start: -10y)
          |> filter(fn: (r) => r["_measurement"] == "gears")
          |> filter(fn: (r) => r["user"] == "{user}" and
                              r["GameName"] == "{GameName}" and
                              r["TrackCode"] == "{TrackCode}" and
                              r["CarModel"] == "{CarModel}")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> filter(fn: (r) => r["DistanceRoundTrack"] >= {start} and r["DistanceRoundTrack"] <= {stop})
          |> group(columns: ["CurrentLap", "SessionId"])
          |> min(column: "Gear")
          |> group()
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 5) // https://docs.influxdata.com/flux/v0.x/stdlib/universe/doubleema/  2 * n - 1
          |> duplicate(column: "Gear", as: "_value")
          |> doubleEMA(n: 3)
          |> keep(columns: ["Gear", "_value", "_time"])
          |> limit(n: 1)
      """.format(
            **vars
        )

        # _LOGGER.debug("query:\n %s", q)
        _LOGGER.debug("querying gear for %s - %s", start, stop)

        # tables = self.query(q)
        query_api = self.client.query_api()

        tables = query_api.query(q)
        if tables:
            return tables[0].records[0].get_value()
        else:
            return 0

    def brake_start(self, segment):
        return self.cache[segment.turn].brake
        # return self.cache["brake_start"].get(brakepoint["corner"])

    def brake_start_q(self, start, stop):
        vars = self.filter.copy()
        vars.update({"start": start - 20, "stop": stop})
        q = """
        from(bucket: "racing")
          |> range(start: -10y)
          |> filter(fn: (r) => r["_measurement"] == "brake_start")
          |> filter(fn: (r) => r["user"] == "{user}" and
                              r["GameName"] == "{GameName}" and
                              r["TrackCode"] == "{TrackCode}" and
                              r["CarModel"] == "{CarModel}")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> filter(fn: (r) => r["DistanceRoundTrack"] >= {start} and r["DistanceRoundTrack"] <= {stop})
          |> group(columns: ["CurrentLap", "SessionId"])
          |> min(column: "DistanceRoundTrack")
          |> group()
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 5) // https://docs.influxdata.com/flux/v0.x/stdlib/universe/doubleema/  2 * n - 1
          |> duplicate(column: "DistanceRoundTrack", as: "_value")
          |> doubleEMA(n: 3)
          |> keep(columns: ["DistanceRoundTrack", "_value", "_time"])
      """.format(
            **vars
        )

        # _LOGGER.debug("query:\n %s", q)
        _LOGGER.debug("querying brake_start for %s - %s", start, stop)

        query_api = self.client.query_api()

        tables = query_api.query(q)
        if tables:
            return tables[0].records[0].get_value()
        else:
            return 0

    def query(self, query):
        return self.client.query_api().query(query)


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
            _LOGGER.info("History thread starting")
            history.run()

        x = threading.Thread(target=history_thread)
        x.start()
    else:
        history.init()
        _LOGGER.info(history.gear_q(100, 250))
