import os
import threading
import logging
import paho.mqtt.client as mqtt
import json

from .session import Session


class Firehose:
    def __init__(self, debug=False, replay=False):
        mqttc = mqtt.Client()
        mqttc.on_message = self.on_message
        mqttc.on_connect = self.on_connect
        mqttc.on_publish = self.on_publish
        mqttc.on_subscribe = self.on_subscribe
        mqttc.username_pw_set(
            os.environ.get("B4MAD_RACING_CLIENT_USER", ""),
            os.environ.get("B4MAD_RACING_CLIENT_PASSWORD", ""),
        )
        self.mqttc = mqttc

        self.replay = replay
        self.debug = debug

        self.sessions = {}
        self._stop_event = threading.Event()

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

        # logging.debug(
        #     "%s: qos='%s',payload='%s'", msg.topic, str(msg.qos), str(msg.payload)
        # )

        if self.stopped():
            self.mqttc.disconnect()

        topic = msg.topic
        if self.replay and topic.startswith("replay/"):
            # remove replay/ prefix from session
            topic = topic[7:]

        try:
            payload = json.loads(msg.payload.decode("utf-8")).get("telemetry")
        except Exception as e:
            logging.error("Error decoding payload: %s", e)
            return

        if topic not in self.sessions:
            try:
                (
                    prefix,
                    driver,
                    session_id,
                    game,
                    track,
                    car,
                    session_type,
                ) = topic.split("/")
            except ValueError:
                # ignore invalid session
                return

            logging.debug(f"New session: {topic}")
            session = Session(topic)
            session.driver = driver
            session.session_id = session_id
            session.game_name = game
            session.track = track
            session.car = car
            session.session_type = session_type
            if self.replay:
                session.session_type = "replay"
            self.sessions[topic] = session

        session = self.sessions[topic]
        session.signal(payload)

    def clear_sessions(self, now):
        delete_sessions = []
        for topic, session in self.sessions.items():
            # delete session without updates for 10 minutes
            if (now - session["end"]).seconds > 600:
                delete_sessions.append(topic)

            # get the length of the session['laps'] list and count down the index
            # and delete the lap if it has the delete flag set
            for i in range(len(session["laps"]) - 1, -1, -1):
                lap = session["laps"][i]
                if lap.get("delete", False):
                    logging.debug(f"{topic}\n\t deleting lap {lap['number']}")
                    del session["laps"][i]

        # delete all sessions by iterating over delete_sessions
        for topic in delete_sessions:
            del self.sessions[topic]
            logging.debug(f"{topic}\n\t deleting inactive session")

    def on_connect(self, mqttc, obj, flags, rc):
        logging.debug("on_connect rc: %s", str(rc))

    def on_publish(self, mqttc, obj, mid):
        # logging.debug("mid: %s", str(mid))
        pass

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        logging.debug(
            "subscribed: mid='%s', granted_qos='%s'", str(mid), str(granted_qos)
        )

    def on_log(self, mqttc, obj, level, string):
        pass

    def run(self):
        self.mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        if self.replay:
            topic = "replay/#"
        else:
            topic = "crewchief/#"

        s = self.mqttc.subscribe(topic, 0)
        if s[0] == mqtt.MQTT_ERR_SUCCESS:
            logging.info(f"Subscribed to {topic}")
            self.mqttc.loop_forever()
        else:
            logging.error(f"Failed to subscribe to {topic}")
