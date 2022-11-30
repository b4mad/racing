// influx task create -f flux/tasks/gears.flux

option task = {
  name: "gears",
  every: 5m,
//   offset: 125m // 2h 5m - my timezone is UTC+2, so timestamps will be offset by 2h
}

data = from(bucket: "racing")
|> range(start: -125m, stop: -120m) // 6 * 60 = 360m
//   |> range(start: -1h)
   |> filter(fn: (r) => r["_measurement"] == "laps_cc")
   |> filter(fn: (r) => (r["_field"] == "Gear" or r["_field"] == "DistanceRoundTrack" or r["_field"] == "CurrentLap"))
// |> filter(fn: (r) => (r["user"] == "durandom") and r["CarModel"] == "Ferrari 488 GT3 Evo 2020" and r["TrackCode"] == "lemans full")
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
