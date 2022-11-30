#!/usr/bin/env python3

import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

q = """
data = from(bucket: "racing")
   |> range(start: %s, stop: %s)
    |> filter(fn: (r) => r["_measurement"] == "laps_cc")
    |> filter(fn: (r) => (r["_field"] == "Brake" or r["_field"] == "DistanceRoundTrack" or r["_field"] == "CurrentLap"))
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> duplicate(column: "Brake", as: "_value")
    |> map(fn: (r) => ({ r with _value: if r._value <= 0.1 then -1.0 else r._value }))
    |> difference(nonNegative: true)
    |> filter(fn: (r) => r["_value"] > 1.0)
    |> drop(columns: ["_value", "host", "topic"])
    |> set(key: "_measurement", value: "brake_start")

data
   |> rename(columns: {Brake: "_value"})
   |> set(key: "_field", value: "Brake")
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
client = InfluxDBClient(url=url, token=token, org=org, timeout=60_000)


start = datetime.datetime(2022, 10, 1, 0, 0)
start = datetime.datetime(2022, 10, 18, 12, 0)
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
        query_api.query_stream(query)
    except InfluxDBError as e:
        print(e)

    start = stop
    stop = start + datetime.timedelta(hours=1)
