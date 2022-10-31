#!/usr/bin/env python3

import os
import json
import daiquiri
import logging

import paho.mqtt.client as mqtt

from coach import Coach
from history import History


daiquiri.setup(level=logging.INFO)
_LOGGER = logging.getLogger("mqtt")
if os.getenv("DEBUG", "1") == "1":
    _LOGGER.setLevel(logging.DEBUG)


CREWCHIEF_USERNAME = os.environ.get("CREWCHIEF_USERNAME", "durandom")
B4MAD_RACING_CLIENT_USER = os.environ.get("B4MAD_RACING_CLIENT_USER", "crewchief")
B4MAD_RACING_CLIENT_PASSWORD = os.environ.get(
    "B4MAD_RACING_CLIENT_PASSWORD", "crewchief"
)


class Mqtt:
    def __init__(self, coach: Coach):
        mqttc = mqtt.Client()
        mqttc.on_message = self.on_message
        mqttc.on_connect = self.on_connect
        mqttc.on_publish = self.on_publish
        mqttc.on_subscribe = self.on_subscribe
        mqttc.username_pw_set(B4MAD_RACING_CLIENT_USER, B4MAD_RACING_CLIENT_PASSWORD)
        self.mqttc = mqttc
        self.coach = coach
        self.topic = ""
        self.do_disconnect = False

    # def __del__(self):
    #     # disconnect from broker

    def disconnect(self):
        self.do_disconnect = True

    def filter_from_topic(self, topic):
        frags = topic.split("/")
        user = frags[1]
        # session = frags[2]
        game = frags[3]
        track = frags[4]
        car = frags[5]
        # track = "summit summit raceway"
        # car = "Ferrari 488 GT3 Evo 2020"
        filter = {
            "user": user,
            "GameName": game,
            "TrackCode": track,
            "CarModel": car,
        }
        return filter

    def on_message(self, mqttc, obj, msg):
        """Handle incoming messages, we are only interested in the telemetry.

        Args:
            mqttc (_type_): the mqtt client
            obj (_type_): the userdata
            msg (_type_): the message received
        """
        _LOGGER.debug(
            "%s: qos='%s',payload='%s'", msg.topic, str(msg.qos), str(msg.payload)
        )

        if self.do_disconnect:
            _LOGGER.debug("stopping MQTT")
            mqttc.disconnect()

        if self.topic != msg.topic:
            _LOGGER.debug("new session %s", msg.topic)
            self.topic = msg.topic
            self.coach.set_filter(self.filter_from_topic(msg.topic))

        # print('.', end='')
        telemetry = json.loads(msg.payload.decode("utf-8"))

        meters = telemetry["telemetry"]["DistanceRoundTrack"]
        response = self.coach.get_response(meters)
        if response:
            _LOGGER.debug("meters: %s, response: %s", meters, response)
            mqttc.publish(f"/coach/{CREWCHIEF_USERNAME}", response)

    def on_connect(self, mqttc, obj, flags, rc):
        _LOGGER.debug("rc: %s", str(rc))

    def on_publish(self, mqttc, obj, mid):
        _LOGGER.debug("mid: %s", str(mid))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        _LOGGER.debug(
            "subscribed: mid='%s', granted_qos='%s'", str(mid), str(granted_qos)
        )

    def on_log(self, mqttc, obj, level, string):
        # print(string)
        pass

    def run(self):
        self.mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        topic = f"crewchief/{CREWCHIEF_USERNAME}/#"
        s = self.mqttc.subscribe(topic, 0)
        if s[0] == mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.info(f"Subscribed to {topic}")
            self.mqttc.loop_forever()
        else:
            _LOGGER.error(f"Failed to subscribe to {topic}")
            exit(1)


if __name__ == "__main__":
    _LOGGER.info("Starting MQTT client")

    history = History()
    coach = Coach(history)

    m = Mqtt(coach)
    m.run()
