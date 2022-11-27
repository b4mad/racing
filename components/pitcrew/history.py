#!/usr/bin/env python3

import threading
import csv
import os
import pickle
import time
import logging
import daiquiri


from influxdb_client import InfluxDBClient
from sanitize_filename import sanitize


daiquiri.setup(level=logging.INFO)
_LOGGER = logging.getLogger("history")
if os.getenv("DEBUG", "1") == "1":
    _LOGGER.setLevel(logging.DEBUG)


B4MAD_RACING_INFLUX_ORG = os.environ.get("B4MAD_RACING_INFLUX_ORG", "b4mad")
B4MAD_RACING_INFLUX_TOKEN = os.environ.get(
    "B4MAD_RACING_INFLUX_TOKEN",
    "citqAMr66LLb25hvaaZm2LezOc88k2ocOFJcJDR6QB-RmLJa_-sAr9kYB4vSFYaz8bt26lm7SokVgpQKdgKFKA==",
)
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
        self.brakepoints = []
        self.brakepoint_idx = 1
        self.previous_brakepoint_idx = 0
        self.ready = False
        self.error = None
        self.do_run = True
        self.clear_cache()

    def stop(self):
        self.do_run = False

    def run(self):
        while self.do_run:
            time.sleep(1)
            if self.do_init:
                self.ready = self.init()
                self.do_init = False

    def set_filter(self, filter):
        self.filter = filter
        self.do_init = True

    def clear_cache(self):
        self.cache = {
            "gear": {},
            "brake_start": {},
        }

    def init(self):
        self.clear_cache()
        if self.init_brakepoints():
            if self.pickle:
                self.read_cache_from_file()
            else:
                self.init_cache()
            self.error = None
            return True
        return False

    def init_cache(self):
        for brakepoint in self.brakepoints:
            if brakepoint["corner"] not in self.cache["gear"]:
                self.cache["gear"][brakepoint["corner"]] = self.gear_q(
                    brakepoint["start"], brakepoint["stop"]
                )
                _LOGGER.debug(
                    "corner %s: avg gear %s",
                    brakepoint["corner"],
                    self.cache["gear"][brakepoint["corner"]],
                )
            if brakepoint["corner"] not in self.cache["brake_start"]:
                self.cache["brake_start"][brakepoint["corner"]] = self.brake_start_q(
                    brakepoint["start"], brakepoint["stop"]
                )
                _LOGGER.debug(
                    "corner %s: avg brake_start %s",
                    brakepoint["corner"],
                    self.cache["brake_start"][brakepoint["corner"]],
                )

    def write_cache_to_file(self):
        with open("cache.pickle", "wb") as outfile:
            pickle.dump(self.cache, outfile)

    def read_cache_from_file(self):
        _LOGGER.debug("reading historic data from file")
        with open("cache.pickle", "rb") as infile:
            self.cache = pickle.load(infile)

    @property
    def brakepoints(self):
        return self._brakepoints

    @brakepoints.setter
    def brakepoints(self, brakepoints):
        self._brakepoints = brakepoints

    def get_brakepoint(self, meters: int) -> dict:
        brakepoint = self.brakepoints[self.brakepoint_idx]
        self.previous_brakepoint = self.brakepoints[self.previous_brakepoint_idx]

        if self.previous_brakepoint_idx < self.brakepoint_idx:
            if (
                meters >= self.previous_brakepoint["stop"]
                and meters < brakepoint["stop"]
            ):
                return brakepoint
        else:
            if (
                meters >= self.previous_brakepoint["stop"]
                or meters < brakepoint["stop"]
            ):
                return brakepoint

        self.previous_brakepoint_idx = self.brakepoint_idx
        self.brakepoint_idx += 1
        if self.brakepoint_idx >= len(self.brakepoints):
            self.brakepoint_idx = 0
        return self.get_brakepoint(meters)

    def init_brakepoints(self) -> bool:
        """Load the brakepoints from the csv file."""
        # get directory of this file
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file = sanitize(f"{self.filter['CarModel']}-{self.filter['TrackCode']}.csv")
        filename = f"{dir_path}/{file}"
        if not os.path.exists(filename):
            _LOGGER.error("no brakepoints found for %s", filename)
            self.error = "no brakepoints found for %s and %s " % (
                self.filter["CarModel"],
                self.filter["TrackCode"],
            )
            return False

        _LOGGER.debug("loading brakepoints from %s", filename)

        self.brakepoints = []
        with open(filename, mode="r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                brakepoint = {}
                for key in row:
                    if row[key]:
                        if key == "mark":
                            brakepoint[key] = row[key]
                        else:
                            brakepoint[key] = int(row[key])
                    else:
                        brakepoint[key] = 0
                brakepoint["corner"] = len(self.brakepoints) + 1
                self.brakepoints.append(brakepoint)
        _LOGGER.debug("loaded %s brakepoints", len(self.brakepoints))
        return True

    def gear(self, brakepoint):
        return self.cache["gear"].get(brakepoint["corner"])

    def gear_q(self, start, stop):
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

        _LOGGER.debug("query:\n %s", q)

        # tables = self.query(q)
        query_api = self.client.query_api()

        tables = query_api.query(q)
        if tables:
            return tables[0].records[0].get_value()
        else:
            return 0

    def brake_start(self, brakepoint):
        return self.cache["brake_start"].get(brakepoint["corner"])

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

        _LOGGER.debug("query:\n %s", q)
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
