#!/usr/bin/env python3

import json
import logging
import os
import threading

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


B4MAD_RACING_MQTT_HOST = os.environ.get("B4MAD_RACING_MQTT_HOST", "telemetry.b4mad.racing")
B4MAD_RACING_MQTT_PORT = int(os.environ.get("B4MAD_RACING_MQTT_PORT", 31883))
B4MAD_RACING_MQTT_USER = os.environ.get("B4MAD_RACING_MQTT_USER", "crewchief")
B4MAD_RACING_MQTT_PASSWORD = os.environ.get("B4MAD_RACING_MQTT_PASSWORD", "crewchief")


class Mqtt:
    def __init__(self, observer, topic, replay: bool = False, debug=False):
        mqttc = mqtt.Client()
        mqttc.on_message = self.on_message
        mqttc.on_connect = self.on_connect
        mqttc.on_publish = self.on_publish
        mqttc.on_subscribe = self.on_subscribe
        mqttc.username_pw_set(B4MAD_RACING_MQTT_USER, B4MAD_RACING_MQTT_PASSWORD)
        self.mqttc = mqttc
        self.do_disconnect = False
        self.replay = replay
        self.topic = topic
        self.observer = observer
        self._stop_event = threading.Event()
        self.ready = False
        self.debug = debug

    # def __del__(self):
    #     # disconnect from broker

    def disconnect(self):
        self.mqttc.disconnect()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def on_message(self, mqttc, obj, msg):
        """Handle incoming messages, we are only interested in the telemetry.

        Args:
            mqttc (_type_): the mqtt client
            obj (_type_): the userdata
            msg (_type_): the message received
        """
        # _LOGGER.debug(
        #     "%s: qos='%s',payload='%s'", msg.topic, str(msg.qos), str(msg.payload)
        # )

        # if self.do_disconnect:
        #     _LOGGER.debug("stopping MQTT")
        #     mqttc.disconnect()

        if self.stopped():
            self.mqttc.disconnect()

        topic = msg.topic
        if self.replay:
            # remove replay/ prefix from session
            topic = topic[7:]

        try:
            payload = json.loads(msg.payload.decode("utf-8")).get("telemetry")
        except Exception as e:
            logging.error("Error decoding payload: %s", e)
            return

        response = self.observer.notify(topic, payload)
        if response:
            (r_topic, r_payload) = response
            payloads = r_payload
            if not isinstance(r_payload, list):
                payloads = [r_payload]

            for r_payload in payloads:
                if self.debug:
                    meters = payload.get("DistanceRoundTrack", 0)
                    logging.debug("r-->: %s: %s : %s", meters, r_topic, r_payload)
                mqttc.publish(r_topic, r_payload)

    def on_connect(self, mqttc, obj, flags, rc):
        _LOGGER.debug("on_connect rc: %s", str(rc))
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self.ready = True

    def on_publish(self, mqttc, obj, mid):
        # _LOGGER.debug("mid: %s", str(mid))
        pass

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        _LOGGER.debug("subscribed: mid='%s', granted_qos='%s'", str(mid), str(granted_qos))

    def on_log(self, mqttc, obj, level, string):
        # print(string)
        pass

    def run(self):
        self.mqttc.connect(B4MAD_RACING_MQTT_HOST, B4MAD_RACING_MQTT_PORT, 60)
        # topic = f"crewchief/{self.driver}/#"
        if self.replay:
            self.topic = f"replay/{self.topic}"

        s = self.mqttc.subscribe(self.topic, 0)
        if s[0] == mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.info(f"Subscribed to {self.topic}")
            self.mqttc.loop_forever()
        else:
            _LOGGER.error(f"Failed to subscribe to {self.topic}")
            exit(1)


# if __name__ == "__main__":
#     _LOGGER.info("Starting MQTT client")

#     history = History()
#     coach = Coach(history)

#     m = Mqtt(coach)
#     m.run()
