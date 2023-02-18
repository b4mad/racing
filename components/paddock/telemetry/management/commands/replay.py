import json
import os
import time
from django.core.management.base import BaseCommand
from telemetry.models import Lap
from telemetry.influx import Influx
import logging
import paho.mqtt.client as mqtt

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
            default=None,
            help="seconds to sleep between messages",
        )
        parser.add_argument("--live", action="store_true")

    def handle(self, *args, **options):
        influx = Influx()
        self.live = options["live"]

        if options["session_ids"]:
            for session_id in options["session_ids"]:
                session = influx.session(
                    session_id=session_id, lap_numbers=options["lap_numbers"]
                )
                if options["new_session_id"]:
                    new_session_id = options["new_session_id"]
                else:
                    new_session_id = int(time.time())
                logging.info(
                    f"Replaying session {session_id} as new session {new_session_id}"
                )
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
                print(topic)
            line_count += 1

            # convert payload to json string
            payload_string = json.dumps(payload)
            # print(payload)
            ltp = payload["telemetry"].get("LapTimePrevious", -1)
            clv = payload["telemetry"].get("CurrentLapIsValid", True)
            plv = payload["telemetry"].get("PreviousLapWasValid", True)
            # current_lap = payload["telemetry"].get("CurrentLap", None)
            # print("CurrentLap:          ", current_lap)
            if ltp > 0 or not clv or not plv:
                print("LapTimePrevious:     ", ltp)
                print("CurrentLapIsValid:   ", clv)
                print("PreviousLapWasValid: ", plv)

            mqttc.publish(topic, payload=str(payload_string), qos=0, retain=False)

            # print dot without newline
            print(".", end="", flush=True)
            print(payload["telemetry"]["DistanceRoundTrack"])
            time.sleep(wait)
