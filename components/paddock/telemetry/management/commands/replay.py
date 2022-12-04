import json
import os
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
        # add argument for list of lap ids as integers separated by commas
        parser.add_argument(
            "-s",
            "--session-ids",
            nargs="+",
            type=int,
            default=None,
            help="list of lap ids to analyze",
        )

    def handle(self, *args, **options):
        i = Influx()
        mqttc = mqtt.Client()
        mqttc.username_pw_set(B4MAD_RACING_CLIENT_USER, B4MAD_RACING_CLIENT_PASSWORD)
        mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        logging.info("Connected to telemetry.b4mad.racing")
        # epoch = datetime.datetime.utcfromtimestamp(0)

        for session_id in options["session_ids"]:
            logging.info(f"Replaying session {session_id}")
            for record in i.session(session_id):
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
                topic = "replay/" + topic
                # print(topic)
                # print dot without newline
                print(".", end="", flush=True)
                # sleep for 1/60th of a second
                # time.sleep(0.016666666666666666)

                # convert payload to json string
                payload = json.dumps(payload)
                # print(payload)

                mqttc.publish(topic, payload=str(payload), qos=0, retain=False)
