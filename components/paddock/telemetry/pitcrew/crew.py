#!/usr/bin/env python3

import os
import threading
import logging
import time
import paho.mqtt.client as mqtt
from telemetry.models import Game, Driver, Car, Track, SessionType, Coach
import json
import django.utils.timezone

from .coach import Coach as PitCrewCoach
from .history import History
from .mqtt import Mqtt

_LOGGER = logging.getLogger("pitcrew")


class Crew:
    def __init__(self):
        mqttc = mqtt.Client()
        mqttc.on_message = self.on_message
        mqttc.on_connect = self.on_connect
        mqttc.on_publish = self.on_publish
        mqttc.on_subscribe = self.on_subscribe
        # mqttc.username_pw_set(env('B4MAD_RACING_CLIENT_USER'), env('B4MAD_RACING_CLIENT_PASSWORD'))
        mqttc.username_pw_set(
            os.environ.get("B4MAD_RACING_CLIENT_USER", ""),
            os.environ.get("B4MAD_RACING_CLIENT_PASSWORD", ""),
        )
        self.mqttc = mqttc
        self.active_sessions = set()
        self.session_cache = {}
        self.active_drivers = set()
        self.active_coaches = {}

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

        prefix, driver, session, game, track, car, session_type = msg.topic.split("/")
        if session not in self.active_sessions:
            logging.info(f"New session: {msg.topic}")
            self.active_sessions.add(session)

            # record = json.loads(msg.payload.decode("utf-8"))
            # logging.debug(record)

            rgame, created = Game.objects.get_or_create(name=game)
            rdriver, created = Driver.objects.get_or_create(name=driver)
            rcar, created = Car.objects.get_or_create(name=car, game=rgame)
            rtrack, created = Track.objects.get_or_create(name=track, game=rgame)
            rsession_type, created = SessionType.objects.get_or_create(
                type=session_type
            )

            now = django.utils.timezone.now()
            rsession, created = rdriver.sessions.get_or_create(
                session_id=session,
                session_type=rsession_type,
                game=rgame,
                defaults={"start": now, "end": now},
            )

            threshold = 500
            if rtrack.length > 100:
                threshold = rtrack.length * 0.1

            self.session_cache[session] = {
                "session": rsession,
                "laps": [],
                "car": rcar,
                "track": rtrack,
                "threshold": threshold,
            }

            if driver.lower() != "jim":
                if driver not in self.active_drivers:
                    print(f"New coach for {driver}")
                    Coach.objects.get_or_create(driver=rdriver)
                    self.active_drivers.add(rdriver)

        payload = json.loads(msg.payload.decode("utf-8"))
        self.analyze(payload, session)

    def analyze(self, payload, session_id):
        now = django.utils.timezone.now()
        telemetry = payload["telemetry"]
        lap_number = telemetry["CurrentLap"]
        lookup = self.session_cache[session_id]
        session = lookup["session"]
        session.end = now
        car = lookup["car"]
        track = lookup["track"]
        length = telemetry["DistanceRoundTrack"]
        time = telemetry["CurrentLapTime"]
        if time < 0:
            time = 0

        # first lap in this session, new lap
        if len(lookup["laps"]) == 0:
            lap = session.new_lap(number=lap_number, car=car, track=track, start=now)
            lookup["laps"].append(lap)
            _LOGGER.info(f"New lap: {lap.pk} for {session_id}")

        lap = lookup["laps"][-1]

        # DistanceRoundTrack is reset to 0 or the pits, new lap
        # driving backwards at least 50 meters
        distance_since_previous_tick = length - lap.length
        if distance_since_previous_tick < -50:
            previous_lap_length = lap.length
            lap = session.new_lap(number=lap_number, car=car, track=track, start=now)
            lookup["laps"].append(lap)
            _LOGGER.info(
                f"New lap: {lap.pk} for {session_id}, length drop from {previous_lap_length} to {length}"
            )

        # set timing
        lap.end = now
        session.end = lap.end

        # lap is valid if started from the beginning, otherwise it is maybe an outlap
        if not lap.valid and 0 <= lap.length < 50:
            _LOGGER.info(f"Marking lap {lap.pk} as valid")
            lap.valid = True

        # only start measuring the lap time if length is larger than the threshold
        if lap.valid and (length > lookup["threshold"]):

            # we just start measuring the lap time
            if lap.time == 0:
                _LOGGER.info(
                    f"start measuring time for {lap.pk} at length {length} (threshold {lookup['threshold']})"
                )
                lap.time = time + 0.001  # add 1ms to avoid start measuring again
                lap.length = length

            # Detect if reset to the pits, then we see a jump in distance
            # how far do we travel since the last tick
            speed = telemetry["SpeedMs"]
            time_delta = time - lap.time

            # only check if we have a time delta larger than 0.1s
            if time_delta > 0.1:
                distance_meter = (speed * time_delta) * 5

                # if we travel more than 5 times the expected meters at current speed, we are in the pits
                if length - lap.length > distance_meter:
                    _LOGGER.info(
                        f"lap {lap.pk} is invalid: jumping from {lap.length} to {length} \
                        is larger than {distance_meter} (5 * {speed}m/s * {time_delta}s )"
                    )
                    lap.valid = False
                else:
                    lap.length = length

    def save_sessions(self):
        while True:
            time.sleep(10)
            _LOGGER.info("saving sessions")
            sessions = self.session_cache.values()
            for session in sessions:
                session["session"].save_dirty_fields()
                track = session["track"]

                for lap in session["laps"]:
                    lap.save_dirty_fields()

                    # if the lap is longer than the track, update the track length
                    # this way we gradually get the correct length
                    lap_length = int(lap.length)
                    if lap.valid and lap_length > track.length:
                        track.refresh_from_db()
                        if lap_length > track.length:
                            _LOGGER.info(
                                f"updating {track.name} length from {track.length} to {lap_length}"
                            )
                            track.length = lap_length
                            track.save()
                            session["threshold"] = track.length * 0.1

    def watch_coaches(self):
        while True:
            time.sleep(11)
            _LOGGER.info("checking coaches")
            coaches = Coach.objects.filter(driver__in=self.active_drivers)
            for coach in coaches:
                _LOGGER.info(f"checking coach for {coach.driver}")
                if coach.enabled:
                    if coach.driver.name not in self.active_coaches.keys():
                        _LOGGER.debug(f"activating coach for {coach.driver}")
                        self.start_coach(coach.driver.name, coach)
                else:
                    if coach.driver.name in self.active_coaches.keys():
                        _LOGGER.debug(f"deactivating coach for {coach.driver}")
                        self.stop_coach(coach.driver)

    def stop_coach(self, driver):
        self.active_coaches[driver.name][0].disconnect()
        self.active_coaches[driver.name][1].disconnect()
        del self.active_coaches[driver.name]

    def start_coach(self, driver, coach):
        history = History()
        coach = PitCrewCoach(history, coach)
        mqtt = Mqtt(coach, driver)

        def history_thread():
            _LOGGER.info(f"History thread starting for {driver}")
            history.run()
            _LOGGER.info(f"History thread stopped for {driver}")

        h = threading.Thread(target=history_thread)

        def mqtt_thread():
            _LOGGER.info(f"MQTT thread starting for {driver}")
            mqtt.run()
            _LOGGER.info(f"MQTT thread stopped for {driver}")

        c = threading.Thread(target=mqtt_thread)

        threads = list()
        threads.append(h)
        threads.append(c)
        c.start()
        h.start()
        self.active_coaches[driver] = [history, mqtt]

    def on_connect(self, mqttc, obj, flags, rc):
        _LOGGER.debug("rc: %s", str(rc))

    def on_publish(self, mqttc, obj, mid):
        _LOGGER.debug("mid: %s", str(mid))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        _LOGGER.debug(
            "subscribed: mid='%s', granted_qos='%s'", str(mid), str(granted_qos)
        )

    def on_log(self, mqttc, obj, level, string):
        pass

    def run(self):
        self.mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        topic = "crewchief/#"
        s = self.mqttc.subscribe(topic, 0)
        if s[0] == mqtt.MQTT_ERR_SUCCESS:
            threading.Thread(target=self.watch_coaches).start()
            threading.Thread(target=self.save_sessions).start()
            _LOGGER.info(f"Subscribed to {topic}")

            self.mqttc.loop_forever()
        else:
            _LOGGER.error(f"Failed to subscribe to {topic}")
            exit(1)
