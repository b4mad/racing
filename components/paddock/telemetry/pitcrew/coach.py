#!/usr/bin/env python3

import logging
import time
from .history import History
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Coach:
    def __init__(self, history: History, db_coach: DbCoach, debug=False):
        self.history = history
        self.previous_history_error = None
        self.db_coach = db_coach
        self.msg = {
            "msg": {},
            "turn": None,
        }
        self.messages = {}
        self.debug = debug

        self.msg_read_interval = 20
        if self.debug:
            self.msg_read_interval = 1

    def set_filter(self, filter):
        self.history.set_filter(filter)
        self.messages = {}

    def gear(self, segment):
        gear_h = self.history.gear(segment)
        if not gear_h:
            return True

        gear = segment.gear
        if abs(gear - gear_h) > 0.2:
            _LOGGER.debug("turn: %s, gear: %s, gear_h: %s", segment.turn, gear, gear_h)
            return True
        return False

    def brake_start(self, segment):
        start = segment.brake
        start_h = self.history.brake_start(segment)

        if not start_h:
            return 10000

        distance_to_ideal = start - start_h  # negative if too late
        if abs(distance_to_ideal) > 10:
            _LOGGER.debug(
                "turn: %s, brake: %s, brake_h: %s",
                segment.turn,
                start,
                start_h,
            )
            return int(distance_to_ideal)
        return False

    def eval_gear(self, segment):
        gear = self.history.driver_gear(segment)
        if segment.gear != gear:
            # enable gear notification
            self.enable_msg(segment)
            return f"gear should be {segment.gear}"
        else:
            self.disable_msg(segment)

    def eval_brake(self, segment):
        brake = self.history.driver_brake(segment)
        delta = segment.brake - brake
        if abs(delta) > 50:
            self.enable_msg(segment)
            logging.debug("%s / %s : delta: %s", brake, segment.brake, delta)
        elif abs(delta) > 10:
            self.disable_msg(segment)
            if delta > 0:
                return "Brake %s meters later" % round(abs(delta))
            else:
                return "Brake %s meters earlier" % round(abs(delta))
        else:
            self.disable_msg(segment)

    def disable_msg(self, segment):
        self.enable_msg(segment, False)

    def enable_msg(self, segment, enabled=True):
        # iterate over messages and enable the one for this segment
        for msg in self.messages.values():
            if "segment" in msg and "enabled" in msg:
                if msg["segment"] == segment:
                    msg["enabled"] = enabled

    def get_response(self, telemetry):
        if not self.history.ready:
            if self.history.error != self.previous_history_error:
                self.previous_history_error = self.history.error
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return self.history.error
            else:
                return None
        # _LOGGER.debug(f"meters: {meters}, msg: {self.msg}")

        now = time.time()
        # build self.messages from fast laps segments
        if not self.messages:
            track_length = self.history.track.length
            for segment in self.history.segments:
                # add gear notification
                if segment.gear:
                    at = (segment.accelerate - 100) % track_length
                    msg = f"gear {segment.gear}"
                    self.messages[at] = {
                        "msg": msg,
                        "read": 0,
                        "enabled": True,
                        "segment": segment,
                    }

                    at = (segment.accelerate + 20) % track_length
                    self.messages[at] = {
                        "fn": self.eval_gear,
                        "args": [segment],
                        "read": 0,
                    }

                if segment.mark == "brake":
                    at = (segment.start - 100) % track_length
                    # This message takes 5.3 seconds to read
                    # msg = "Brake in 3 .. 2 .. 1 .. brake"                    # This message takes 5.3 seconds to read
                    msg = "Brake %s in 100" % (round(segment.force / 10) * 10)
                    self.messages[at] = {
                        "msg": msg,
                        "read": 0,
                        "enabled": True,
                    }

                    at = (segment.brake + 20) % track_length
                    self.messages[at] = {
                        "fn": self.eval_brake,
                        "args": [segment],
                        "read": 0,
                    }

                if segment.mark == "throttle":
                    at = (segment.start - 100) % track_length
                    to = round(segment.force / 10) * 10
                    if to > 0:
                        msg = "Throttle to %s in 100" % to
                    else:
                        msg = "Lift throttle in 100"
                    self.messages[at] = {
                        "msg": msg,
                        "read": 0,
                        "enabled": True,
                    }

            logging.debug(f"loaded messages: {self.messages}")

        # loop over all messages and check the distance, if we have something to say
        meters = telemetry["DistanceRoundTrack"]
        self.history.update(now, telemetry)
        for at in self.messages:
            distance = abs(at - meters)
            # only read every 20 seconds and if we are close
            msg = self.messages[at]
            if "enabled" in msg and not msg["enabled"]:
                continue
            if distance < 2 and now - msg["read"] > self.msg_read_interval:
                if "fn" in self.messages[at]:
                    self.messages[at]["read"] = now
                    message = self.messages[at]["fn"](*self.messages[at]["args"])
                    if message:
                        return message
                else:
                    self.messages[at]["read"] = now
                    return self.messages[at]["msg"]

        return None

        meters = telemetry["DistanceRoundTrack"]
        speed = telemetry["SpeedMs"]
        segment = self.history.segment(meters)
        # logging.debug(f"{meters}: {segment}")
        if not segment:
            return None

        if self.msg["turn"] != segment.turn:
            self.msg["turn"] = segment.turn
            self.msg["msg"] = {}

            # announce segment start if debugging
            if self.debug:
                self.msg["msg"][meters + 5] = f"Turn {segment.turn}"

            # do we have something to say about the current segment?
            if self.gear(segment):
                # coach on correct gear

                at = segment.start + 100
                self.msg["msg"][at] = "Gear %s" % segment.gear
                _LOGGER.debug(f"meters: {meters}, msg: {self.msg}")

            brake = self.brake_start(segment)
            if brake and self.debug:
                # calculate where we are in 5.3 seconds
                travel_distance = speed * 5.3
                # print(f"travel_distance: {travel_distance} at speed: {speed}")
                at = segment.brake - travel_distance
                self.msg["msg"][at] = "Brake in 3 .. 2 .. 1 .. brake"
                # if abs(brake) > 50:
                #     self.msg["msg"][at] = segment["mark"]
                # elif brake > 0:
                #     self.msg["msg"][at] = "Brake %s meters earlier" % brake
                # else:
                #     self.msg["msg"][at] = "Brake %s meters later" % abs(brake)
                _LOGGER.debug(f"meters: {meters}, msg: {self.msg}")

        # loop over all messages and check the distance, if we have something to say
        for at in self.msg["msg"]:
            distance = abs(at - meters)
            if distance < 2:
                return self.msg["msg"].pop(at)

        return None


if __name__ == "__main__":
    history = History()
    history.pickle = True
    coach = Coach(history)

    track = "okayama full"
    track_length = 3500
    track = "summit summit raceway"
    track_length = 3000

    car = "Ferrari 488 GT3 Evo 2020"
    filter = {
        "user": "durandom",
        "GameName": "iRacing",
        "TrackCode": track,
        "CarModel": car,
    }
    coach.set_filter(filter)
    history.init()
    # history.write_cache_to_file()

    for j in range(1, 4):
        _LOGGER.info("lap %s", j)
        for i in range(0, track_length):
            response = coach.get_response(i)
            # time.sleep(0.2)
            if response:
                _LOGGER.info("meters: %s, response: %s", i, response)
