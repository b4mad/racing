#!/usr/bin/env python3

import datetime

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

q = """
data = from(bucket: "racing")
|> range(start: %s, stop: %s)
   |> filter(fn: (r) => r["_measurement"] == "laps_cc")
   |> filter(fn: (r) => (r["_field"] == "Gear" or r["_field"] == "DistanceRoundTrack" or r["_field"] == "CurrentLap"))
   |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
   |> duplicate(column: "Gear", as: "_value")
   |> difference(keepFirst: true, columns: ["_value"])
   |> filter(fn: (r) => r["_value"] != 0 or not exists r["_value"])
   |> filter(fn: (r) => r["Gear"] > 0)
   |> drop(columns: ["_value", "host", "topic"])
   |> set(key: "_measurement", value: "gears")

data
   |> rename(columns: {Gear: "_value"})
   |> set(key: "_field", value: "Gear")
   |> to(bucket: "racing")

data
   |> rename(columns: {CurrentLap: "_value"})
   |> set(key: "_field", value: "CurrentLap")
   |> to(bucket: "racing")

data
   |> rename(columns: {DistanceRoundTrack: "_value"})
   |> set(key: "_field", value: "DistanceRoundTrack")
   |> to(bucket: "racing")
"""

org = "b4mad"
token = "PFmq_uLsJ8NZXYuq9zBbNsCbxuerXIapE4N_2kjLzyWauLyZqbscrEJRJw25upSJ1-tKJQAJa8GfItx7Sl4SOw=="
url = "https://telemetry.b4mad.racing/"
client = InfluxDBClient(url=url, token=token, org=org)


start = datetime.datetime(2022, 10, 1, 0, 0)
start = datetime.datetime(2022, 10, 18, 11, 0)
stop = start + datetime.timedelta(hours=1)
now = datetime.datetime.now()
query_api = client.query_api()

while stop < now:
    print(start)

    range = {
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": stop.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    query = q % (range["from"], range["to"])
    try:
        query_api.query(query)
    except InfluxDBError as e:
        print(e)

    start = stop
    stop = start + datetime.timedelta(hours=1)
