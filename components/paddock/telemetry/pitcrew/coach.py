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

    def disable_msg(self, segment):
        self.enable_msg(segment, False)

    def enable_msg(self, segment, enabled=True):
        # iterate over messages and enable the one for this segment
        for at in self.messages:
            msg = self.messages[at]
            if "segment" in msg and "enabled" in msg:
                if msg["segment"] == segment:
                    if isinstance(msg["msg"], str):
                        if msg["enabled"] != enabled:
                            msg["enabled"] = enabled
                            logging.debug(f"at {at}: {msg['msg']} enabled: {enabled}")

    def new_msg(self, at, msg, segment):
        message = {
            "msg": msg,
            "read": 0,
            "enabled": True,
            "segment": segment,
        }
        at = at % self.history.track_length
        while at in self.messages:
            at += 1
            at = at % self.history.track_length
        self.messages[at] = message
        return message

    def new_fn(self, at, fn, segment):
        message = self.new_msg(at, fn, segment)
        message["args"] = [segment]
        message["kwargs"] = {}
        return message

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

        # build self.messages from fast laps segments
        if not self.messages:
            self.init_messages()
            # self.init_messages_debug()
            for at in self.messages:
                logging.debug(f"at {at}: {self.messages[at]['msg']}")

        now = time.time()
        # loop over all messages and check the distance, if we have something to say
        distance_round_track = telemetry["DistanceRoundTrack"]
        self.history.update(now, telemetry)
        for at in self.messages:
            distance = abs(at - distance_round_track)
            # only read every 20 seconds and if we are close
            msg = self.messages[at]
            if "enabled" in msg and not msg["enabled"]:
                continue
            if distance <= 1 and now - msg["read"] > self.msg_read_interval:
                msg = self.messages[at]["msg"]
                if isinstance(msg, str):
                    self.messages[at]["read"] = now
                    return msg
                if callable(msg):
                    self.messages[at]["read"] = now
                    kwargs = self.messages[at]["kwargs"].copy()
                    kwargs["telemetry"] = telemetry
                    kwargs["at"] = at
                    message = msg(*self.messages[at]["args"], **kwargs)
                    if message:
                        return message

    def eval_brake_debug(self, brake_start, **kwargs):
        telemetry = kwargs["telemetry"]
        distance_round_track = telemetry["DistanceRoundTrack"]
        speed_ms = self.history.driver_speed_at(brake_start)
        driver_brake_start = self.history.driver_brake_start(
            brake_start, distance_round_track
        )

        if driver_brake_start:
            delta = int(brake_start - driver_brake_start)
            ratio = delta / speed_ms
            logging.debug(
                "eval_brake: %s / %s : delta: %s speed: %.0f  ratio: %.2f",
                brake_start,
                driver_brake_start,
                delta,
                speed_ms,
                ratio,
            )
            return f"delta: {delta} ratio {ratio:.2f}"
        else:
            logging.debug(
                "eval_brake: %s / %s : no driver_brake_start",
                brake_start,
                driver_brake_start,
            )

    def init_messages_debug(self):
        self.track_length = self.history.track.length
        for at in range(0, self.track_length, 500):
            self.new_msg(at, "brake", None)
            brake_point = at + 100
            self.new_msg(brake_point, "now", None)
            msg = self.new_fn(brake_point + 100, self.eval_brake_debug, None)
            msg["args"] = [brake_point]

    def init_messages(self):
        speed_factor = 1.2
        self.track_length = self.history.track.length
        for segment in self.history.segments:
            if segment.mark == "brake":
                at = segment.start - (3.5 * segment.speed * speed_factor)
                # This message takes 5.3 seconds to read
                # msg = "Brake in 3 .. 2 .. 1 .. brake"                    # This message takes 5.3 seconds to read
                msg = "%s percent" % (round(segment.force / 10) * 10)
                self.new_msg(at, msg, segment)

                # 1.2 is calculated by init_messages_debug stuff
                #    brake+delta=actual
                #    ratio=delta/speed
                #    delta=ratio*speed
                at = segment.start - (segment.speed * speed_factor)
                msg = "brake"
                self.new_msg(at, msg, segment)

                at = segment.end + 20
                self.new_fn(at, self.eval_brake, segment)

            if segment.mark == "throttle":
                at = segment.start - (3 * segment.speed * speed_factor)
                to = round(segment.force / 10) * 10
                msg = "throttle to %s" % to
                self.new_msg(at, msg, segment)

                at = segment.start
                msg = "now"
                self.new_msg(at, msg, segment)

            if segment.gear:
                at = segment.start - (4.5 * segment.speed * speed_factor)
                msg = f"gear {segment.gear}"
                self.new_msg(at, msg, segment)

                at = segment.end + 60
                self.new_fn(at, self.eval_gear, segment)

    def eval_gear(self, segment, **kwargs):
        gear = self.history.driver_gear(segment)
        if segment.gear != gear:
            # enable gear notification
            self.enable_msg(segment)
            # return f"gear should be {segment.gear}"
        else:
            self.disable_msg(segment)

    def eval_brake(self, segment, **kwargs):
        driver_brake_start = self.history.driver_brake(segment)
        delta = segment.start - driver_brake_start
        logging.debug(
            "eval_brake: %s / %s : delta: %s", driver_brake_start, segment.start, delta
        )
        if abs(delta) > 50:
            self.enable_msg(segment)
        elif abs(delta) > 10:
            self.enable_msg(segment)
        #     self.disable_msg(segment)
        #     if delta > 0:
        #         return "Brake %s meters later" % round(abs(delta))
        #     else:
        #         return "Brake %s meters earlier" % round(abs(delta))
        else:
            self.disable_msg(segment)


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
