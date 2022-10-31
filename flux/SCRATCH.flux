// schema exploration
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "racing", tag: "CarClass")

import "influxdata/influxdb/schema"
class = schema.tagValues(bucket: "racing", tag: "CarClass")
model = schema.tagValues(bucket: "racing", tag: "CarModel")


// A single metric
from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "laps")
  |> filter(fn: (r) => r._field == "TrackPositionPercent")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")

// join
brake = from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "Brake")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)

// list Sessions
from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "Gear")
  |> keep(columns: ["GameName", "user", "CarModel", "TrackCode", "SessionId", "_time", "_value"])
  |> sort(columns: ["_time"], desc: false)
  |> first()
  |> group(columns: [])
  |> drop(columns: ["_value"])

// annotations
from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
//  |> range(start: -2d, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "CurrentLap")
  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)
  |> sort(columns: ["_time"])
  |> keep(columns: ["_time", "_value"])
  |> yield(name: "mean")

// get SessionId
from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "Gear")
  |> keep(columns: ["SessionId"])
  |> distinct(column: "SessionId")

// variable filtering
// https://community.grafana.com/t/grafana-influxdb-flux-query-for-displaying-multi-select-variable-inputs/35536/14



x = from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "world_x")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)

join(tables: {brake: brake, x: x}, on: ["_time"] )
  |> keep(columns: ["_value_brake", "_value_x"])
  |> sort(columns: ["_value_x"], desc: false)


from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> keyValues(keyColumns: ["CarClass"])
  |> group()
  |> keep(columns: ["CarClass"])
  |> distinct(columns: ["CarClass"])

from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> group(columns: ["CarClass"], mode:"by")
  |> count()


from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> group(columns: ["CarClass"], mode:"by")
  |> count()



from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> group(columns: ["CarClass"], mode:"by")
  |> count()
  |> map(fn: (r) => ({r with _value: float(v: r._value)}))
  |> histogram(
        bins: linearBins(start: 0.0, width: 5000.0, count: 10, infinity: true),
        normalize: true
  )

// CarModels
from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "laps")
  |> keyValues(keyColumns: ["CarModel"])
  |> group()
  |> keep(columns: ["CarModel"])
  |> distinct(column: "CarModel")


from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop:v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "Brake" or r["_field"] == "Clutch" or r["_field"] == "Throttle"
                    or contains(value: r._CarModel, set: ${CarModel:json})
                    or contains(value: r._CarClass, set: ${CarClass:json})
                    )
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")

from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop:v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => (r["_field"] == "Brake" or r["_field"] == "Clutch" or r["_field"] == "Throttle"))
  |> group(columns: ["CarModel", "_field"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")

from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop:v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => (r["_field"] == "Brake" or r["_field"] == "Clutch" or r["_field"] == "Throttle"))
  |> group(columns: ["CarModel", "_field"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")

from(bucket: "racing")
  |> range(start: 2022-04-29T07:28:32.729Z, stop:2022-04-29T07:30:51.993Z)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "Brake" or r["_field"] == "Clutch" or r["_field"] == "Throttle"
                    and( contains(value: r.CarModel, set: ["Mazda MX-5 Cup"]) and contains(value: r.CarClass, set: ["MX5 Cup 2016","Rallycross","SBRS"]))
                    )
  |> aggregateWindow(every: 200ms, fn: mean, createEmpty: false)
  |> yield(name: "mean")


from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop:v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => (
           (r["_field"] == "Brake" or r["_field"] == "Clutch" or r["_field"] == "Throttle")
       and (
         contains(value: r.CarModel, set: ${CarModel:json})
        )
       ))
  |> group(columns: ["CarModel", "_field"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")



from(bucket: "racing")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "laps")
  |> filter(fn: (r) => r["_field"] == "CurrentLap")
  |> group(columns: ["SessionId", "UserId", "GameName", "TrackCode", "CarModel", "user"])
  |> count()
  |> yield(name: "mean")




https://grafana.com/grafana/dashboards/15356

https://www.sqlpac.com/en/documents/influxdb-v2-flux-language-quick-reference-guide-cheat-sheet.html
