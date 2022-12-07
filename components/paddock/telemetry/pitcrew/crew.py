#!/usr/bin/env python3

import os
import threading
import logging
import time
import paho.mqtt.client as mqtt
from telemetry.models import Game, Driver, Car, Track, SessionType, Coach
import json
import django.utils.timezone
import locked_dict.locked_dict as locked_dict

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
        mqttc.username_pw_set(
            os.environ.get("B4MAD_RACING_CLIENT_USER", ""),
            os.environ.get("B4MAD_RACING_CLIENT_PASSWORD", ""),
        )
        self.mqttc = mqttc
        self.active_sessions = set()
        self.sessions = locked_dict.LockedDict()
        self.active_drivers = set()
        self.active_coaches = {}
        self.replay = False

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

        session = msg.topic
        if self.replay:
            # remove replay/ prefix from session
            session = session[7:]

        now = django.utils.timezone.now()

        if session not in self.active_sessions:
            logging.info(f"New session: {session}")
            self.active_sessions.add(session)
            self.sessions[session] = {
                "start": now,
                "end": now,
                "laps": [],
            }

            try:
                (
                    prefix,
                    driver,
                    session_id,
                    game,
                    track,
                    car,
                    session_type,
                ) = session.split("/")
            except ValueError:
                # ignore invalid session
                return

            if driver.lower() != "jim":
                if driver not in self.active_drivers:
                    rdriver, created = Driver.objects.get_or_create(name=driver)
                    try:
                        coach, created = Coach.objects.get_or_create(driver=rdriver)
                        if created:
                            logging.info(f"New coach for {driver}")
                    except Exception as e:
                        logging.error("Error creating coach: %s", e)
                        return
                    self.active_drivers.add(rdriver)

        try:
            payload = json.loads(msg.payload.decode("utf-8")).get("telemetry")
        except Exception as e:
            logging.error("Error decoding payload: %s", e)
            return
        self.analyze(payload, session, now)

    def analyze(self, telemetry, session_id, now):
        session = self.sessions.get(session_id)
        session["end"] = now
        length = telemetry.get("DistanceRoundTrack", None)
        speed = telemetry.get("SpeedMs", None)
        lap_time = telemetry.get("CurrentLapTime", None)
        current_lap = telemetry.get("CurrentLap", None)

        if length is None or speed is None or lap_time is None or current_lap is None:
            logging.error("Invalid telemetry: %s", telemetry)
            logging.error(
                f"\tlength: {length}, speed: {speed}, lap_time: {lap_time}, current_lap: {current_lap}"
            )
            return

        threshold = speed * 0.5
        new_lap = False
        previous_length = -1
        if len(session["laps"]) == 0:
            #  start a new lap if
            #  * DistanceOnTrack starts at 0 # we drive over the finish line
            #    we're sampling a 60hz, with the speed we should see a lap start
            #      (speed * 0.16) meters past the finish line
            if length < threshold:
                new_lap = True
        else:
            lap = session["laps"][-1]
            previous_length = lap["length"]
            # start a new lap if cross the finish line
            if length < threshold and length < lap["length"]:
                _LOGGER.info(
                    f"{session_id}\n\t finishing lap at length {previous_length}"
                    + f" and time {lap['time']}"
                )
                lap["finished"] = True
                new_lap = True

        if new_lap:
            lap = {
                "start": now,
                "end": now,
                "length": length,
                "time": lap_time,
                "finished": False,
                "number": current_lap,
                "active": lap_time
                < 5,  # if time is less than 5 seconds, lap is active,
                "inactive_log_time": now,
            }
            session["laps"].append(lap)
            _LOGGER.info(
                f"{session_id}\n\t new lap length {length} < threshold {threshold}"
                + f" and < previous lap length {previous_length}, active: {lap['active']}, time: {lap_time}"
            )

            # get the length of the session['laps'] list and count down the index
            for i in range(len(session["laps"]) - 1, -1, -1):
                if session["laps"][i].get("delete", False):
                    del session["laps"][i]
            return

        if len(session["laps"]) > 0:
            lap = session["laps"][-1]

            if lap["active"]:
                # mark not active if we jump back more than 50 meters
                distance_since_previous_tick = length - lap["length"]
                if distance_since_previous_tick < -50:
                    _LOGGER.info(
                        f"{session_id}\n\t lap not active, jump {distance_since_previous_tick}m\n"
                        + f"\t\t lap length {lap['length']} jumped to length {length}"
                    )
                    lap["active"] = False
                    return

                # FIXME mark not active if we cut the track

                previous_lap_time = lap["time"]
                if lap_time < previous_lap_time:
                    _LOGGER.info(
                        f"{session_id}\n\t stop measuring time at {lap_time}s for {previous_lap_time}s / {length}m"
                    )
                    lap["active"] = False
                else:
                    lap["end"] = now
                    lap["length"] = length
                    lap["time"] = lap_time
            elif (lap_time < lap["time"] or lap_time == 0) and lap["start"] == lap[
                "end"
            ]:
                # start measuring time if we're past the threshold and the time started
                #  some games have a delay on CurrentLapTime
                _LOGGER.info(
                    f"{session_id}\n\t start measuring time at lap.time {lap['time']} / time {lap_time}"
                )
                lap["active"] = True
                lap["end"] = now
                lap["length"] = length
                lap["time"] = lap_time
            else:
                if (now - lap["inactive_log_time"]).seconds > 120:
                    lap["inactive_log_time"] = now
                    _LOGGER.info(
                        f"{session_id}\n\t lap not active, time {lap_time} > lap.time {lap['time']}"
                    )

    def save_sessions(self):
        while True:
            time.sleep(10)
            # FIXME: purge old sessions
            session_ids = self.sessions.keys()
            for session_id in session_ids:
                session = self.sessions.get(session_id)
                (
                    prefix,
                    driver,
                    session_number,
                    game,
                    track,
                    car,
                    session_type,
                ) = session_id.split("/")

                # save session to database
                session_record = session.get("record", None)
                if session_record is None:
                    try:
                        rdriver, created = Driver.objects.get_or_create(name=driver)
                        rgame, created = Game.objects.get_or_create(name=game)
                        rsession_type, created = SessionType.objects.get_or_create(
                            type=session_type
                        )
                        rcar, created = Car.objects.get_or_create(name=car, game=rgame)
                        rtrack, created = Track.objects.get_or_create(
                            name=track, game=rgame
                        )
                        session_record, created = rdriver.sessions.get_or_create(
                            session_id=session_number,
                            session_type=rsession_type,
                            game=rgame,
                            defaults={"start": session["start"], "end": session["end"]},
                        )
                        session["record"] = session_record
                        session["car"] = rcar
                        session["track"] = rtrack
                    except Exception as e:
                        logging.error(f"Error saving session {session_number}: {e}")
                        continue

                # iterate over laps with index
                for i, lap in enumerate(session["laps"]):
                    if lap["finished"]:
                        # check if lap length is within 98% of the track length
                        track = session["track"]
                        track_length = track.length

                        if lap["length"] > track_length * 0.98:
                            try:
                                lap_record = session_record.laps.create(
                                    number=lap["number"],
                                    car=session["car"],
                                    track=track,
                                    start=lap["start"],
                                    end=lap["end"],
                                    length=lap["length"],
                                    valid=True,
                                    time=lap["time"],
                                )
                                _LOGGER.info(
                                    f"Saving lap {lap_record} for session {session_id}"
                                )
                                session_record.end = session["end"]
                                session_record.save_dirty_fields()
                            except Exception as e:
                                logging.error(f"Error saving lap {lap['number']}: {e}")
                        else:
                            lstring = (
                                f"{lap['number']}: {lap['time']}s {lap['length']}m"
                            )
                            _LOGGER.info(
                                f"Discard lap {lstring} for session {session_id} - track length {track_length}m"
                            )
                        lap["delete"] = True

                        lap_length = int(lap["length"])
                        if lap_length > track.length:
                            track.refresh_from_db()
                            if lap_length > track.length:
                                _LOGGER.info(
                                    f"updating {track.name} length from {track.length} to {lap_length}"
                                )
                                track.length = lap_length
                                track.save()

    def watch_coaches(self):
        while True:
            time.sleep(11)
            # _LOGGER.info("checking coaches")
            coaches = Coach.objects.filter(driver__in=self.active_drivers)
            for coach in coaches:
                # _LOGGER.info(f"checking coach for {coach.driver}")
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

    def start_coach(self, driver, coach, debug=False):
        history = History()
        coach = PitCrewCoach(history, coach, debug=debug)
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
        if self.replay:
            topic = "replay/#"
        else:
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
