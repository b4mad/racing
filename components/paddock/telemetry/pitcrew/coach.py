#!/usr/bin/env python3

import json
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
        self.debug_data = {}
        self.json_response = db_coach.driver.name == "durandom"

        self.msg_read_interval = 20
        if self.debug:
            self.msg_read_interval = 1

    def set_filter(self, filter):
        self.history.set_filter(filter)
        self.messages = {}

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
                if callable(msg):
                    self.messages[at]["read"] = now
                    kwargs = self.messages[at]["kwargs"].copy()
                    kwargs["telemetry"] = telemetry
                    kwargs["at"] = at
                    message = msg(*self.messages[at]["args"], **kwargs)
                    if message:
                        return message
                elif isinstance(msg, dict):
                    self.messages[at]["read"] = now
                    return json.dumps(msg)
                else:
                    self.messages[at]["read"] = now
                    return msg

    def init_messages(self):
        self.track_length = self.history.track.length
        for segment in self.history.segments:
            if segment.mark == "brake":
                gear = ""
                if segment.gear:
                    gear = f"gear {segment.gear} "
                text = gear + "%s percent" % (round(segment.force / 10) * 10)
                at = segment.start
                self.new_msg_done_by(at, text, segment)

                at = segment.start
                text = "brake"
                msg = self.schedule_msg(at, text, segment)
                # msg = self.new_msg(at, text, segment)

                at = segment.end + 20
                self.new_fn(at, self.eval_brake, segment, brake_msg_at=msg["at"])

            if segment.mark == "throttle":
                at = segment.start - 100
                to = round(segment.force / 10) * 10
                text = "throttle to %s" % to
                self.new_msg_done_by(at, text, segment)

                at = segment.start
                text = "now"
                self.schedule_msg(at, text, segment)
                # self.new_msg(at, text, segment)

            # if segment.gear:
            #     at = segment.start - 80
            #     text = f"gear {segment.gear}"
            #     self.new_msg(at, text, segment)

            #     at = segment.end + 60
            #     self.new_fn(at, self.eval_gear, segment)

    def eval_gear(self, segment, **kwargs):
        pass
        # gear = self.history.driver_gear(segment)
        # if segment.gear != gear:
        #     # enable gear notification
        #     self.enable_msg(segment)
        #     # return f"gear should be {segment.gear}"
        # else:
        #     self.disable_msg(segment)

    def eval_brake(self, segment, **kwargs):
        # driver_brake_start = self.history.driver_brake(segment)
        meters = kwargs["telemetry"]["DistanceRoundTrack"]
        driver_brake_start = self.history.t_start_distance(
            segment.start - 50, segment.end, "Brake"
        )
        delta = driver_brake_start - segment.start
        # brake_msg_at = kwargs["brake_msg_at"]
        # time_brake_msg_at = self.history.t_at_distance(
        #     brake_msg_at, "CurrentLapTime"
        # )
        time_segment_at = self.history.t_at_distance(segment.start, "CurrentLapTime")
        time_driver_brake_start = self.history.t_at_distance(
            driver_brake_start, "CurrentLapTime"
        )
        # time_delta = time_brake_msg_at - time_driver_brake_start
        time_delta = time_driver_brake_start - time_segment_at
        speed = self.history.t_at_distance(driver_brake_start, "SpeedMs")

        debug_deltas = self.debug_data.get("deltas", [])
        if abs(time_delta) < 0.5:
            debug_deltas.append(time_delta)
        self.debug_data["deltas"] = debug_deltas

        logging.debug(
            "eval_brake: %i driver: %i - segment: %i : delta: %i, time_delta: %.2f, speed: %i, avg_time_delta: %.2f",
            meters,
            driver_brake_start,
            segment.start,
            delta,
            time_delta,
            speed,
            self.debug_data["deltas"]
            and sum(self.debug_data["deltas"]) / len(self.debug_data["deltas"])
            or 0,
        )
        # logging.debug(f"deltas: {self.debug_data.get('deltas', [])}")
        # if abs(delta) > 50:
        #     self.enable_msg(segment)
        # elif abs(delta) > 10:
        #     self.enable_msg(segment)
        #     self.disable_msg(segment)
        #     if delta > 0:
        #         return "Brake %s meters later" % round(abs(delta))
        #     else:
        #         return "Brake %s meters earlier" % round(abs(delta))
        # else:
        #     self.disable_msg(segment)

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

    def msg_read_time(self, msg):
        # count the number of words
        words = len(msg.split(" "))
        return words * 0.8  # avg ms per word

    def new_msg(self, at, msg, segment, finish_reading_at=False):
        message = {
            "msg": msg,
            "read": 0,
            "enabled": True,
            "segment": segment,
            "at": at,
        }
        at = at % self.history.track_length

        # there's a delay of x seconds to read the message at the requested meters
        # offset = 1.0  # time_delta 0.1
        offset = 1.1
        offset = 0

        # if the message should be finished at the requested meters
        if finish_reading_at:
            read_time = self.msg_read_time(msg)
            offset += read_time

        if offset:
            new_at = self.history.offset_distance(at, seconds=offset)
            logging.debug(f"offset {offset:.2f} seconds: {at} -> {new_at}")
            at = new_at
        while at in self.messages:
            at += 1
            at = at % self.history.track_length
        self.messages[at] = message
        message["at"] = at
        return message

    def new_msg_done_by(self, at, msg, segment):
        return self.new_msg(at, msg, segment, finish_reading_at=True)

    def schedule_msg(self, at, msg, segment):
        if self.json_response:
            respond_at = at - 50
            payload = {
                "message": msg,
                "distance": at,
                "priority": 9,
            }
            return self.new_msg(respond_at, payload, segment)
        else:
            return self.new_msg(at, msg, segment)

    def new_fn(self, at, fn, segment, **kwargs):
        message = self.new_msg(at, fn, segment)
        message["args"] = [segment]
        message["kwargs"] = kwargs
        return message

    # debug stuff
    def brake_debug(self, segment, **kwargs):
        telemetry = kwargs["telemetry"]
        self.brake_debug_time = telemetry["CurrentLapTime"]
        return "now"

    def eval_brake_debug(self, brake_start, **kwargs):
        telemetry = kwargs["telemetry"]
        distance_round_track = telemetry["DistanceRoundTrack"]
        speed_ms = self.history.driver_speed_at(brake_start)
        driver_brake_start = self.history.driver_brake_start(
            brake_start, distance_round_track
        )

        real_brake_time = self.history.driver_telemetry_start(
            brake_start, distance_round_track, field="CurrentLapTime"
        )
        time_delta = real_brake_time - self.brake_debug_time

        if driver_brake_start:
            delta = int(brake_start - driver_brake_start)
            ratio = delta / speed_ms
            logging.debug(
                "eval_brake: %s / %s : delta: %s speed: %.0f ratio: %.2f time_delta: %.2f",
                brake_start,
                driver_brake_start,
                delta,
                speed_ms,
                ratio,
                time_delta,
            )
            return f"delta: {delta:.0f}"
        else:
            logging.debug(
                "eval_brake: %s / %s : no driver_brake_start",
                brake_start,
                driver_brake_start,
            )

    def init_messages_debug(self):
        self.track_length = self.history.track.length
        self.brake_debug_time = 0
        # for at in range(0, self.track_length, 500):
        #     self.new_msg(at, "brake", None)
        #     brake_point = at + 100
        #     # self.new_msg(brake_point, "now", None)
        #     # this message says "now" and stores the time
        #     msg = self.new_fn(brake_point, self.brake_debug, None)
        #     # this message calculates the delta
        #     msg = self.new_fn(brake_point + 100, self.eval_brake_debug, None)
        #     msg["args"] = [brake_point]
        for at in range(0, self.track_length, 100):
            msg = {
                "message": "brake",
                "meters": at + 50,
                "priority": 10,
            }
            self.new_msg(at, msg, None)


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
