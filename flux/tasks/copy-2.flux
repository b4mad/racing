// import "join"

option task = {
  name: "copy",
  every: 1d,
}


import "sql"
left =
    from(bucket: "racing")
        |> range(start: -1h)
        |> filter(fn: (r) => r._measurement == "laps_cc")

right =
    sql.from(
        driverName: "postgres",
        dataSourceName: "postgresql://paddock:A..a@telemetry.b4mad.racing:31884/paddock",
        query: "SELECT 1670307078 as session_id",
    )

join.inner(
    left: left,
    right: right,
    on: (l, r) => l.SessionId == r.session_id,
    as: (l, r) => ({l}),
)


// session_info = from(bucket: "racing")
//   |> range(start: -1d)
//   |> filter(fn: (r) => r._measurement == "session_info")
//   |> keep(columns: ["SessionId"])
//   |> distinct()
//   |> limit(n: 1)

// from(bucket: "racing")
//   |> range(start: -1d)
//   |> filter(fn: (r) => r._measurement == "laps_cc" and r.SessionId in session_info)
//   |> to(bucket: "racing", fieldFn: (r) => ({r with _measurement: "fast_laps"}))
