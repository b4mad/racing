import json
import os
import time
from django.core.management.base import BaseCommand
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
            "-l",
            "--lap-ids",
            nargs="*",
            type=int,
            default=None,
            help="list of lap ids to analyze",
        )
        parser.add_argument(
            "-w",
            "--wait",
            nargs="?",
            type=int,
            default=None,
            help="fraction of a second to sleep between messages",
        )

    def handle(self, *args, **options):
        influx = Influx()
        mqttc = mqtt.Client()
        mqttc.username_pw_set(B4MAD_RACING_CLIENT_USER, B4MAD_RACING_CLIENT_PASSWORD)
        mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        logging.info("Connected to telemetry.b4mad.racing")
        # epoch = datetime.datetime.utcfromtimestamp(0)
        sleep = 0
        if options["wait"]:
            sleep = 1.0 / options["wait"]

        for session_id in options["session_ids"]:
            logging.info(f"Replaying session {session_id}")
            line_count = 0
            for record in influx.session(session_id, lap_ids=options["lap_ids"]):
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
                topic = f"replay/{prefix}/durandom/{session_id}/{game}/{track}/{car}/{session_type}"

                if line_count == 0:
                    print(topic)
                line_count += 1

                # print dot without newline
                print(".", end="", flush=True)
                if sleep:
                    time.sleep(sleep)

                # convert payload to json string
                payload = json.dumps(payload)
                # print(payload)

                mqttc.publish(topic, payload=str(payload), qos=0, retain=False)
