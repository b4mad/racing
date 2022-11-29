#!/usr/bin/env python3

import logging
from .history import History
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Coach:
    def __init__(self, history: History, db_coach: DbCoach):
        self.history = history
        self.previous_history_error = None
        self.db_coach = db_coach
        self.msg = {
            "msg": {},
            "at": None,
            "corner": None,
        }

    def set_filter(self, filter):
        self.history.set_filter(filter)

    def gear(self, brakepoint):
        gear = brakepoint["gear"]
        gear_h = self.history.gear(brakepoint)

        if not gear_h:
            return True

        if abs(gear - gear_h) > 0.2:
            _LOGGER.debug(
                "corner: %s, gear: %s, gear_h: %s", brakepoint["corner"], gear, gear_h
            )
            return True
        return False

    def brake_start(self, brakepoint):
        start = brakepoint["start"]
        start_h = self.history.brake_start(brakepoint)

        if not start_h:
            return 10000

        distance_to_ideal = start - start_h  # negative if too late
        if abs(distance_to_ideal) > 10:
            _LOGGER.debug(
                "corner: %s, brake: %s, brake_h: %s",
                brakepoint["corner"],
                start,
                start_h,
            )
            return int(distance_to_ideal)
        return False

    def get_response(self, meters):
        if not self.history.ready:
            if self.history.error != self.previous_history_error:
                self.previous_history_error = self.history.error
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return self.history.error
            else:
                return None

        brakepoint = self.history.get_brakepoint(meters)

        if self.msg["corner"] != brakepoint["corner"]:
            self.msg["corner"] = brakepoint["corner"]
            self.msg["msg"] = {}

            # do we have something to say about the current corner?
            if self.gear(brakepoint):
                # coach on correct gear
                at = brakepoint["start"] - 100  # 100 meters before corner
                self.msg["msg"][at] = "Shift down to gear %s" % brakepoint["gear"]

            brake = self.brake_start(brakepoint)
            if brake:
                # coach on correct gear
                at = brakepoint["start"] - 500  # 100 meters before corner
                if abs(brake) > 50:
                    self.msg["msg"][at] = brakepoint["mark"]
                elif brake > 0:
                    self.msg["msg"][at] = "Brake %s meters earlier" % brake
                else:
                    self.msg["msg"][at] = "Brake %s meters later" % abs(brake)

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
