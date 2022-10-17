#!/usr/bin/env python3

import threading
import csv
import os
import pickle
import time
from influxdb_client import InfluxDBClient
import logging

logging.basicConfig(level=logging.DEBUG)


class History:
    def __init__(self):
        org = "b4mad"
        token = "PFmq_uLsJ8NZXYuq9zBbNsCbxuerXIapE4N_2kjLzyWauLyZqbscrEJRJw25upSJ1-tKJQAJa8GfItx7Sl4SOw=="
        url = "https://telemetry.b4mad.racing/"
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.pickle = False
        self.do_init = False
        self.brakepoints = []
        self.brakepoint_idx = 1
        self.previous_brakepoint_idx = 0
        self.clear_cache()

    def run(self):
        while True:
            time.sleep(1)
            if self.do_init:
                self.init()
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
        # if time.time() - self.last_refresh > 120: # refresh every 2 minutes
        #     logging.debug("refreshing history")
        #     self.filter_from_topic()
        self.clear_cache()
        self.init_brakepoints()
        if self.pickle:
            self.read_cache_from_file()
        else:
            self.init_cache()

    def init_cache(self):
        for brakepoint in self.brakepoints:
            if brakepoint["corner"] not in self.cache["gear"]:
                self.cache["gear"][brakepoint["corner"]] = self.gear_q(
                    brakepoint["start"], brakepoint["stop"]
                )
                logging.debug(
                    "corner %s: avg gear %s",
                    brakepoint["corner"],
                    self.cache["gear"][brakepoint["corner"]],
                )
            if brakepoint["corner"] not in self.cache["brake_start"]:
                self.cache["brake_start"][brakepoint["corner"]] = self.brake_start_q(
                    brakepoint["start"], brakepoint["stop"]
                )
                logging.debug(
                    "corner %s: avg brake_start %s",
                    brakepoint["corner"],
                    self.cache["brake_start"][brakepoint["corner"]],
                )

    def write_cache_to_file(self):
        with open("cache.pickle", "wb") as outfile:
            pickle.dump(self.cache, outfile)

    def read_cache_from_file(self):
        logging.debug("reading historic data from file")
        with open("cache.pickle", "rb") as infile:
            self.cache = pickle.load(infile)

    @property
    def brakepoints(self):
        return self._brakepoints

    @brakepoints.setter
    def brakepoints(self, brakepoints):
        self._brakepoints = brakepoints

    def get_brakepoint(self, meters):
        if not self.brakepoints:
            return None

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

    def init_brakepoints(self) -> None:
        """Load the brakepoints from the csv file."""
        # get directory of this file
        dir_path = os.path.dirname(os.path.realpath(__file__))
        filename = (
            f"{dir_path}/{self.filter['CarModel']}-{self.filter['TrackCode']}.csv"
        )
        logging.debug("loading brakepoints from %s", filename)

        self.brakepoints = []
        with open(filename, mode="r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                brakepoint = {}
                for key in row:
                    if row[key]:
                        brakepoint[key] = int(row[key])
                    else:
                        brakepoint[key] = 0
                brakepoint["corner"] = len(self.brakepoints) + 1
                self.brakepoints.append(brakepoint)
        logging.debug("loaded %s brakepoints", len(self.brakepoints))

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

        # logging.debug("query:\n %s", q)

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

        # logging.debug("query:\n %s", q)
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
            logging.info("History thread starting")
            history.run()

        x = threading.Thread(target=history_thread)
        x.start()
    else:
        history.init()
        print(history.gear_q(100, 250))
