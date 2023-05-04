import json
import os
import time
import datetime
import threading

from django.core.management.base import BaseCommand
from django.utils import timezone
from telemetry.models import Lap
from telemetry.influx import Influx
from telemetry.pitcrew.firehose import Firehose
from telemetry.pitcrew.session_saver import SessionSaver
import logging
import paho.mqtt.client as mqtt
from rich.console import Console
from rich.table import Column
from rich.progress import Progress, TextColumn

B4MAD_RACING_MQTT_HOST = os.environ.get(
    "B4MAD_RACING_MQTT_HOST", "telemetry.b4mad.racing"
)
B4MAD_RACING_MQTT_PORT = int(os.environ.get("B4MAD_RACING_MQTT_PORT", 31883))
B4MAD_RACING_MQTT_USER = os.environ.get("B4MAD_RACING_MQTT_USER", "crewchief")
B4MAD_RACING_MQTT_PASSWORD = os.environ.get("B4MAD_RACING_MQTT_PASSWORD", "crewchief")


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
            help="set new session id",
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
        parser.add_argument("--firehose", action="store_true")
        parser.add_argument("--start", type=str, default=None)
        parser.add_argument("--end", type=str, default=None)
        parser.add_argument("--change-driver", type=str, default=None)
        parser.add_argument("--bucket", type=str, default="racing")
        parser.add_argument("--measurement", type=str, default="laps_cc")
        parser.add_argument("--delta", type=str, default=None)
        parser.add_argument("--quiet", action="store_true")
        parser.add_argument("--keep-session-id", action="store_true")

    def handle(self, *args, **options):
        influx = Influx()
        self.live = options["live"]
        self.console = Console()
        text_column = TextColumn("{task.fields[meters]}", table_column=Column(ratio=1))
        # bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
        self.progress = Progress(text_column, expand=True)
        self.task = self.progress.add_task("Replaying", total=100, meters=0, topic="")
        self.change_driver = options["change_driver"]
        self.keep_session_id = options["keep_session_id"]
        self.quiet = options["quiet"]
        self.session_saver = None
        self.session_save_thread = None
        bucket = options["bucket"]
        measurement = options["measurement"]

        if options["firehose"]:
            self.firehose = Firehose()
            self.observer = self.firehose_notify
            if self.live:
                self.session_saver = SessionSaver(self.firehose)
                self.session_saver.sleep_time = 5
                self.session_save_thread = threading.Thread(
                    target=self.session_saver.run
                )
                self.session_save_thread.name = "session_saver"
                logging.debug("starting Thread session_saver")
                self.session_save_thread.start()
        else:
            # FIXME: use mqtt class
            self.mqttc = mqtt.Client()
            self.mqttc.username_pw_set(
                B4MAD_RACING_MQTT_USER, B4MAD_RACING_MQTT_PASSWORD
            )
            self.mqttc.connect(B4MAD_RACING_MQTT_HOST, B4MAD_RACING_MQTT_PORT, 60)
            self.observer = self.mqtt_notify

        if options["session_ids"]:
            for session_id in options["session_ids"]:
                session = influx.session(
                    session_id=session_id,
                    lap_numbers=options["lap_numbers"],
                    start=options["start"],
                    end=options["end"],
                    bucket=bucket,
                    measurement=measurement,
                )
                if options["new_session_id"]:
                    new_session_id = options["new_session_id"]
                else:
                    new_session_id = int(time.time())
                msg = f"[green] Replaying session {session_id} as new session {new_session_id}"
                self.progress.console.print(msg)
        elif options["lap_ids"]:
            for lap_id in options["lap_ids"]:
                lap = Lap.objects.get(id=lap_id)
                session = influx.session(
                    lap=lap,
                    bucket=bucket,
                    measurement=measurement,
                )
                if options["new_session_id"]:
                    new_session_id = options["new_session_id"]
                else:
                    new_session_id = int(time.time())
                msg = (
                    f"[green] Replaying lap_id {lap_id} as new session {new_session_id}"
                )
                self.progress.console.print(msg)
        else:
            session = influx.raw_stream(
                start=options["start"],
                end=options["end"],
                bucket=bucket,
                measurement=measurement,
                delta=options["delta"],
            )
            new_session_id = None
            msg = f"[green] Replaying from start {options['start']} to end {options['end']}"
            self.progress.console.print(msg)

        with self.progress:
            self.replay(session, wait=options["wait"], new_session_id=new_session_id)

        if self.session_save_thread:
            self.session_saver.stop()
            self.session_save_thread.join()
            self.session_saver.save_sessions()

    def firehose_notify(self, topic, payload):
        now = timezone.make_aware(
            datetime.datetime.fromtimestamp(payload["time"] / 1000)
        )

        self.firehose.notify(topic, payload["telemetry"], now=now)

    def mqtt_notify(self, topic, payload):
        # convert payload to json string
        payload_string = json.dumps(payload)
        self.mqttc.publish(topic, payload=str(payload_string), qos=0, retain=False)

    def replay(self, session, wait=0.001, new_session_id=None):
        logging.info("Connected to telemetry.b4mad.racing")
        # epoch = datetime.datetime.utcfromtimestamp(0)

        prev_payload = {"telemetry": {}}
        monitor_fields = [
            "LapTimePrevious",
            "CurrentLapIsValid",
            "PreviousLapWasValid",
            "CurrentLap",
            # "CurrentLapTime",
        ]
        monitor_fields_in_payload = {}
        for field in monitor_fields:
            monitor_fields_in_payload[field] = True
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
            if self.keep_session_id:
                new_session_id = session_id
            if self.change_driver:
                driver = self.change_driver

            if self.live:
                topic = f"{prefix}/{driver}/{new_session_id}/{game}/{track}/{car}/{session_type}"
            else:
                topic = f"replay/{prefix}/{driver}/{new_session_id}/{game}/{track}/{car}/{session_type}"

            if line_count == 0:
                self.progress.console.print(f"[bold blue] {topic}")
            line_count += 1

            # self.progress.console.print_json(payload_string)

            distance_round_track = payload["telemetry"].get("DistanceRoundTrack", 0)
            if not self.quiet:
                self.progress.update(
                    self.task, advance=1, meters=distance_round_track, topic=topic
                )

            for field in monitor_fields:
                try:
                    value = payload["telemetry"][field]
                    prev_value = prev_payload["telemetry"].get(field)
                    if value != prev_value:
                        if not self.quiet:
                            self.progress.console.print(
                                f"{distance_round_track}: {field}: {prev_value} -> {value}"
                            )
                except KeyError:
                    if monitor_fields_in_payload[field]:
                        monitor_fields_in_payload[field] = False
                        msg = f"[red] {field} not in payload"
                        self.progress.console.print(msg)
            self.observer(topic, payload)
            prev_payload = payload
            time.sleep(wait)
