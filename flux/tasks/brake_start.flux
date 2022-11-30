// influx task create -f flux/tasks/brake_start.flux

option task = {
  name: "brake_start",
  every: 5m,
//   offset: 125m // 2h 5m - my timezone is UTC+2, so timestamps will be offset by 2h
}

data = from(bucket: "racing")
    |> range(start: -125m, stop: -120m) // 6 * 60 = 360m
//    |> range(start: -1d)
    |> filter(fn: (r) => r["_measurement"] == "laps_cc")
//    |> filter(fn: (r) => r["SessionId"] == "1666105269")
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
