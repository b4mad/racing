option task = {
  name: "delete",
  every: 1d,
}

option time_range = 10y

from(bucket: "racing")
  |> range(start: -time_range, stop: -1w)
  |> filter(fn: (r) => r._measurement == "laps_cc")
