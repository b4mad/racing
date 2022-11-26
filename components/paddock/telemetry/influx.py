import os
import influxdb_client


class Influx:
    def __init__(self):
        # configure influxdb client
        org = "b4mad"
        token = os.environ.get(
            "INFLUXDB_TOKEN",
            "citqAMr66LLb25hvaaZm2LezOc88k2ocOFJcJDR6QB-RmLJa_-sAr9kYB4vSFYaz8bt26lm7SokVgpQKdgKFKA==",
        )
        url = "https://telemetry.b4mad.racing/"
        self.influx = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        self.query_api = self.influx.query_api()

    def sessions(self, start="-1d", stop="now()"):
        query = f"""
            import "influxdata/influxdb/schema"
            schema.tagValues(
                bucket: "racing",
                tag: "SessionId",
                start: {start},
                stop: {stop}
            )
        """
        records = self.query_api.query_stream(query=query)
        for record in records:
            yield record["_value"]

    def session(self, session_id):
        query = f"""
            from(bucket: "racing")
            |> range(start: -10y, stop: now())
            |> filter(fn: (r) => r["_measurement"] == "laps_cc")
            |> filter(fn: (r) => r["SessionId"] == "{session_id}")
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

        records = self.query_api.query_stream(query=query)
        for record in records:
            yield record


# def track(influx):
#     query_api = influx.query_api()
#     query = f"""
#     from(bucket: "racing")
#         |> range(start:-10d, stop: now())
#         |> filter(fn: (r) => r._field == "DistanceRoundTrack" )
#         |> last()
#         |> limit(n: 1)
#     """

#     records = query_api.query_stream(org=ORG, query=query)

#     tracks = {}
#     engine = create_engine(models.construct_connection_string(), echo=True)
#     session = Session(engine)

#     for record in records:
#         name = record["TrackCode"]
#         length = record["_value"]
#         if name not in tracks:
#             track = Track(name=name, length=length)
#             tracks[name] = track
#             session.add(track)
#         else:
#             track = tracks[name]
#             if length > track.length:
#                 track.length = length

#     session.commit()


# def init_db():
#     engine = create_engine(models.construct_connection_string(), echo=True)
#     models.drop_tables(engine)
#     models.create_tables(engine)


# if __name__ == "__main__":
#     if os.getenv("DEBUG", "1") == "1":
#         _LOGGER.setLevel(logging.DEBUG)
#         _LOGGER.debug("Debug mode enabled")

#     # logging.debug("")
#     # init_db()
#     # sessions(influx)
#     for session in sessions(influx):
#         print(session)
#         analyze_session(session, influx)
