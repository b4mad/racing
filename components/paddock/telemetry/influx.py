from datetime import datetime
import logging

import os
import csv

import influxdb_client

import warnings
from influxdb_client.client.warnings import MissingPivotFunction

warnings.simplefilter("ignore", MissingPivotFunction)


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

    def laps_from_file(self, filename="tracks.csv"):
        tracks = {}
        # open csv file with track data and read it into dictionary
        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["game"] not in tracks:
                    tracks[row["game"]] = {}
                if row["track"] not in tracks[row["game"]]:
                    tracks[row["game"]][row["track"]] = {}
                if row["car"] not in tracks[row["game"]][row["track"]]:
                    tracks[row["game"]][row["track"]][row["car"]] = {}
                if row["session"] not in tracks[row["game"]][row["track"]][row["car"]]:
                    tracks[row["game"]][row["track"]][row["car"]][row["session"]] = []
                tracks[row["game"]][row["track"]][row["car"]][row["session"]].append(
                    {
                        "lap": row["lap"],
                        "start": row["start"],
                        "end": row["end"],
                        "time": row["time"],
                        "length": row["length"],
                    }
                )
        self.tracks = tracks

    def telemetry_for(self, game="", track="", car=""):
        data = []
        fgame = game
        ftrack = track
        fcar = car
        for game, tracks in self.tracks.items():
            for track, cars in tracks.items():
                for car, sessions in cars.items():
                    if game != fgame or track != ftrack or car != fcar:
                        continue
                    for session, laps in sessions.items():
                        for lap in laps:
                            lap_number = lap["lap"]
                            lap_time = lap["time"]
                            length = lap["length"]
                            logging.info(
                                f"Processing {game} {track} : {session} - {lap_number: >2} : {length} - {lap_time}"
                            )
                            # 2022-12-05 19:52:18.141110+00:00
                            start = datetime.strptime(
                                lap["start"], "%Y-%m-%d %H:%M:%S.%f%z"
                            )
                            end = datetime.strptime(
                                lap["end"], "%Y-%m-%d %H:%M:%S.%f%z"
                            )

                            df = self.session_df(
                                session, lap_number=lap["lap"], start=start, end=end
                            )
                            data.append(df)
        return data

    def telemetry_for_laps(self, laps=[]):
        data = []
        for lap in laps:
            game = lap.session.game.name
            session = lap.session.session_id
            track = lap.track.name
            car = lap.car.name
            lap_number = lap.number

            logging.info(
                f"Processing {game} {track} {car} : {session} - {lap_number: >2} : {lap.length} - {lap.time}"
            )

            try:
                df = self.session_df(
                    session, lap_number=lap_number, start=lap.start, end=lap.end
                )
                data.append(df)
            except Exception as e:
                logging.error(e)

        return data

    def session(self, session_id, lap_ids=[]):
        query = f"""
            from(bucket: "racing")
            |> range(start: -10y, stop: now())
            |> filter(fn: (r) => r["_measurement"] == "laps_cc")
            |> filter(fn: (r) => r["SessionId"] == "{session_id}")
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

        lap_filter = []
        if lap_ids:
            for lap_id in lap_ids:
                lap_filter.append(f'r["CurrentLap"] == "{lap_id}"')

            query += f"|> filter(fn: (r) => {' or '.join(lap_filter)})"

        # print(query)

        records = self.query_api.query_stream(query=query)
        for record in records:
            yield record

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

    def session_df(self, session_id, lap_number=None, start="-1d", end="now()"):
        if type(start) == datetime:
            start = start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if type(end) == datetime:
            end = end.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        query = f"""
        from(bucket: "racing")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r["_measurement"] == "laps_cc")
        |> filter(fn: (r) => r["SessionId"] == "{session_id}")
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> filter(fn: (r) => r["CurrentLap"] == "{lap_number}")
        |> sort(columns: ["_time"], desc: false)
        """

        df = self.query_api.query_data_frame(query=query)
        if df.empty:
            raise Exception(f"No data found for {session_id} lap {lap_number}")

        game = df["GameName"].iloc[0]
        if game == "Assetto Corsa Competizione":
            # flip y axis
            df["x"] = df["WorldPosition_x"]
            df["y"] = df["WorldPosition_z"] * -1
        if game == "Automobilista 2":
            df["x"] = df["WorldPosition_x"]
            df["y"] = df["WorldPosition_z"]

        df["id"] = df["SessionId"].astype(str) + "-" + df["CurrentLap"].astype(str)

        df = df[df["Gear"] != 0]

        return df


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
