#!/usr/bin/env python3

import json
import logging
import django.utils.timezone
from .history import History
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Coach:
    def __init__(self, history: History, db_coach: DbCoach, debug=False):
        self.history = history
        self.previous_history_error = None
        self.db_coach = db_coach
        self.messages = []
        self.previous_distance = 0
        self.debug = debug
        self.debug_data = {}
        # self.json_response = db_coach.driver.name == "durandom"
        self.json_response = True

        self.response_topic = f"/coach/{db_coach.driver.name}"

        self.topic = ""

    def filter_from_topic(self, topic):
        frags = topic.split("/")
        driver = frags[1]
        # session = frags[2]
        game = frags[3]
        track = frags[4]
        car = frags[5]
        filter = {
            "Driver": driver,
            "GameName": game,
            "TrackCode": track,
            "CarModel": car,
        }
        return filter

    def notify(self, topic, payload, now=None):
        now = now or django.utils.timezone.now()
        if self.topic != topic:
            self.topic = topic
            logging.debug("new session %s", topic)
            self.set_filter(self.filter_from_topic(topic))

        response = self.get_response(payload, now)
        if response:
            return (self.response_topic, response)

    def set_filter(self, filter):
        self.history.set_filter(filter)
        self.messages = []

    def get_response(self, telemetry, now):
        # FIXME: refactor all this init stuff into an init method
        if not self.history.ready:
            if self.history.error != self.previous_history_error:
                self.previous_history_error = self.history.error
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return self.history.error
            else:
                return None

        self.history.update(now, telemetry)

        if not self.messages:
            self.init_messages()

        distance_round_track = telemetry["DistanceRoundTrack"]
        if distance_round_track < self.previous_distance:
            self.messages = self.sort_messages(distance_round_track)

        next_message = self.messages[0]
        distance = abs(next_message["at"] - distance_round_track)

        if distance < 10:
            self.messages.append(self.messages.pop(0))
            msg = next_message["msg"]
            if callable(msg):
                kwargs = next_message["kwargs"].copy()
                kwargs["telemetry"] = telemetry
                kwargs["at"] = next_message["at"]
                response = msg(*next_message["args"], **kwargs)
                if response:
                    return response
            elif isinstance(msg, dict):
                return json.dumps(msg)
            else:
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
                self.schedule_msg_done_by(at, text, segment)

                at = segment.start
                text = "brake"
                msg = self.schedule_msg(at, text, segment)

                at = segment.end + 20
                self.new_fn(at, self.eval_brake, segment, brake_msg_at=msg["at"])

            if segment.mark == "throttle":
                at = segment.start - 100
                to = round(segment.force / 10) * 10
                text = "throttle to %s" % to
                self.schedule_msg_done_by(at, text, segment)

                at = segment.start
                text = "now"
                self.schedule_msg(at, text, segment)

    def sort_messages(self, distance):
        # sort messages by distance, keyword argument 'at'
        messages = sorted(self.messages, key=lambda k: k["at"])
        index_of_first_item = 0

        # loop through messages and find index of first item larger than distance
        for i, msg in enumerate(messages):
            index_of_first_item = i
            if msg["at"] > distance:
                break

        return messages[index_of_first_item:] + messages[:index_of_first_item]

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
        driver_brake_start = self.history.t_start_distance(segment.start - 50, segment.end, "Brake")
        delta = driver_brake_start - segment.start
        # brake_msg_at = kwargs["brake_msg_at"]
        # time_brake_msg_at = self.history.t_at_distance(
        #     brake_msg_at, "CurrentLapTime"
        # )
        time_segment_at = self.history.t_at_distance(segment.start, "CurrentLapTime")
        time_driver_brake_start = self.history.t_at_distance(driver_brake_start, "CurrentLapTime")
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
            self.debug_data["deltas"] and sum(self.debug_data["deltas"]) / len(self.debug_data["deltas"]) or 0,
        )

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

    def new_msg(self, at, msg, segment):
        message = {
            "msg": msg,
            "enabled": True,
            "segment": segment,
            "at": at,
        }

        at = at % self.history.track_length
        message["at"] = at
        self.messages.append(message)
        return message

    def schedule_msg(self, at, msg, segment):
        read_time = self.msg_read_time(msg)
        respond_at = self.history.offset_distance(at, seconds=read_time)
        payload = {
            "message": msg,
            "distance": at,
            "priority": 9,
        }
        return self.new_msg(respond_at, payload, segment)

    def new_msg_done_by(self, at, msg, segment):
        read_time = self.msg_read_time(msg)
        new_at = self.history.offset_distance(at, seconds=read_time)
        return self.new_msg(new_at, msg, segment)

    def schedule_msg_done_by(self, at, msg, segment):
        read_time = self.msg_read_time(msg)
        new_at = self.history.offset_distance(at, seconds=read_time)
        return self.schedule_msg(new_at, msg, segment)

    def new_fn(self, at, fn, segment, **kwargs):
        message = self.new_msg(at, fn, segment)
        message["args"] = [segment]
        message["kwargs"] = kwargs
        return message

    # FIXME: refactor the offset code
    def new_msg_old(self, at, msg, segment, finish_reading_at=False):
        message = {
            "msg": msg,
            "enabled": True,
            "segment": segment,
            "at": at,
        }

        at = at % self.history.track_length

        # there's a delay of x seconds to read the message at the requested meters
        # offset = 1.0  # time_delta 0.1
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
        message["at"] = at
        self.messages.append(message)
        return message
