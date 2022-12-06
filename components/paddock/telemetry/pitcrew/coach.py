#!/usr/bin/env python3

import logging
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
        self.debug = debug

    def set_filter(self, filter):
        self.history.set_filter(filter)

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
