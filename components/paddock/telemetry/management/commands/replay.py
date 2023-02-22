import json
import os
import time
from django.core.management.base import BaseCommand
from telemetry.models import Lap
from telemetry.influx import Influx
import logging
import paho.mqtt.client as mqtt
from rich.console import Console
from rich.table import Column
from rich.progress import Progress, TextColumn

B4MAD_RACING_CLIENT_USER = os.environ.get("B4MAD_RACING_CLIENT_USER", "crewchief")
B4MAD_RACING_CLIENT_PASSWORD = os.environ.get(
    "B4MAD_RACING_CLIENT_PASSWORD", "crewchief"
)


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--session-ids",
            nargs="+",
            type=int,
            default=None,
            help="list of sessions to replay",
        )
        parser.add_argument(
            "-n",
            "--new-session-id",
            nargs="?",
            type=int,
            default=None,
            help="list of sessions to replay",
        )
        parser.add_argument(
            "-i",
            "--lap-ids",
            nargs="*",
            type=int,
            default=None,
            help="lap id to analyze",
        )
        parser.add_argument(
            "-l",
            "--lap-numbers",
            nargs="*",
            type=int,
            default=None,
            help="lap numbers to analyze",
        )
        parser.add_argument(
            "-w",
            "--wait",
            nargs="?",
            type=float,
            default=0.001,
            help="seconds to sleep between messages",
        )
        parser.add_argument("--live", action="store_true")
        parser.add_argument("--start", type=str, default=None)
        parser.add_argument("--end", type=str, default=None)

    def handle(self, *args, **options):
        influx = Influx()
        self.live = options["live"]
        self.console = Console()
        text_column = TextColumn("{task.fields[meters]}", table_column=Column(ratio=1))
        # bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
        self.progress = Progress(text_column, expand=True)
        self.task = self.progress.add_task("Replaying", total=100, meters=0, topic="")
        if options["session_ids"]:
            for session_id in options["session_ids"]:
                session = influx.session(
                    session_id=session_id,
                    lap_numbers=options["lap_numbers"],
                    start=options["start"],
                    end=options["end"],
                )
                if options["new_session_id"]:
                    new_session_id = options["new_session_id"]
                else:
                    new_session_id = int(time.time())
                msg = f"[green] Replaying session {session_id} as new session {new_session_id}"
                self.progress.console.print(msg)

                with self.progress:
                    self.replay(
                        session, wait=options["wait"], new_session_id=new_session_id
                    )

        if options["lap_ids"]:
            for lap_id in options["lap_ids"]:
                lap = Lap.objects.get(id=lap_id)
                session = influx.session(lap=lap)
                if options["new_session_id"]:
                    new_session_id = options["new_session_id"]
                else:
                    new_session_id = int(time.time())
                logging.info(
                    f"Replaying lap_id {lap_id} as new session {new_session_id}"
                )
                self.replay(
                    session, wait=options["wait"], new_session_id=new_session_id
                )

    def replay(self, session, wait=0.001, new_session_id=None):
        mqttc = mqtt.Client()
        mqttc.username_pw_set(B4MAD_RACING_CLIENT_USER, B4MAD_RACING_CLIENT_PASSWORD)
        mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        logging.info("Connected to telemetry.b4mad.racing")
        # epoch = datetime.datetime.utcfromtimestamp(0)

        prev_payload = {"telemetry": {}}
        monitor_fields = [
            "LapTimePrevious",
            "CurrentLapIsValid",
            "PreviousLapWasValid",
            "CurrentLap",
        ]
        line_count = 0
        for record in session:
            topic = record["topic"]
            _time = record["_time"]
            values = record.values.copy()
            for key in [
                "result",
                "table",
                "_start",
                "_stop",
                "_time",
                "_measurement",
                "topic",
                "host",
            ]:
                del values[key]

            for key in [
                "CarModel",
                "GameName",
                "SessionId",
                "SessionTypeName",
                "TrackCode",
                "user",
            ]:
                del values[key]

            # publish to mqtt
            # convert _time to seconds

            # _time = (_time - epoch).total_seconds() * 1000.0
            _time = int(_time.timestamp() * 1000.0)
            payload = {
                "time": _time,
                "telemetry": values,
            }
            (
                prefix,
                driver,
                session_id,
                game,
                track,
                car,
                session_type,
            ) = topic.split("/")
            if self.live:
                topic = f"{prefix}/durandom/{new_session_id}/{game}/{track}/{car}/{session_type}"
            else:
                topic = f"replay/{prefix}/durandom/{new_session_id}/{game}/{track}/{car}/{session_type}"

            if line_count == 0:
                self.progress.console.print(f"[bold blue] {topic}")
            line_count += 1

            # convert payload to json string
            payload_string = json.dumps(payload)

            distance_round_track = payload["telemetry"].get("DistanceRoundTrack", 0)
            self.progress.update(
                self.task, advance=1, meters=distance_round_track, topic=topic
            )

            for field in monitor_fields:
                value = payload["telemetry"].get(field, None)
                prev_value = prev_payload["telemetry"].get(field, None)
                if value != prev_value:
                    self.progress.console.print(
                        f"{distance_round_track}: {field}: {prev_value} -> {value}"
                    )

            # ltp = payload["telemetry"].get("LapTimePrevious", None)
            # clv = payload["telemetry"].get("CurrentLapIsValid", None)
            # plv = payload["telemetry"].get("PreviousLapWasValid", None)
            # # current_lap = payload["telemetry"].get("CurrentLap", None)
            # # print("CurrentLap:          ", current_lap)
            # if ltp > 0 or not clv or not plv:
            #     print("LapTimePrevious:     ", ltp)
            #     print("CurrentLapIsValid:   ", clv)
            #     print("PreviousLapWasValid: ", plv)

            mqttc.publish(topic, payload=str(payload_string), qos=0, retain=False)

            # print dot without newline
            # print(".", end="", flush=True)
            # print(payload["telemetry"]["DistanceRoundTrack"])
            prev_payload = payload
            time.sleep(wait)
