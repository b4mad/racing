#!/usr/bin/env python3

import json
import logging
from typing import Any
import django.utils.timezone
from .history import History, Segment
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Message:
    def __init__(self, history, **kwargs):
        self.history = history
        self.track_length = self.history.track.length

        self.at = kwargs.get("at", 0)
        self.msg = kwargs.get("msg", "")
        self.segment = kwargs.get("segment", Segment(self.history))
        self.enabled = kwargs.get("enabled", True)
        self.json_respone = kwargs.get("json_respone", True)
        self.related = kwargs.get("related", [])
        self.silent = kwargs.get("silent", False)
        self.args = kwargs.get("args", [])
        self.kwargs = kwargs.get("kwargs", {})

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "at" and self.track_length:
            __value = __value % self.track_length
        super().__setattr__(__name, __value)

    def response(self):
        text_to_read = self.msg
        if callable(self.msg):
            kwargs = self.kwargs.copy()
            # kwargs["message"] = self
            text_to_read = self.msg(self, *self.args, **kwargs)

        if not self.silent and self.json_respone and text_to_read:
            return json.dumps(
                {
                    "distance": self.at,
                    "message": text_to_read,
                    "priority": 9,
                }
            )

        if not self.silent and text_to_read:
            return text_to_read

    def silence(self):
        if not self.silent:
            logging.debug(f"silencing '{self.msg}'")
            self.silent = True

    def louden(self):
        if self.silent:
            logging.debug(f"loudening '{self.msg}'")
            self.silent = False

    def read_time(self):
        if not self.msg:
            raise Exception("no message - can't calculate read time")
        words = len(self.msg.split(" "))
        return words * 0.8  # avg ms per word

    def finish_at(self, at=None):
        if not at:
            at = self.at
        read_time = self.read_time()
        respond_at = self.history.offset_distance(at, seconds=read_time)
        self.at = respond_at


class Coach:
    def __init__(self, history: History, db_coach: DbCoach, debug=False):
        self.history = history
        self.previous_history_error = None
        self.db_coach = db_coach
        self.messages = []
        self.previous_distance = 10_000_000
        self.response_topic = f"/coach/{db_coach.driver.name}"
        self.topic = ""

    def new_msg(self, **kwargs):
        message = Message(history=self.history)
        for key, value in kwargs.items():
            message[key] = value
        self.messages.append(message)
        return message

    # def disable_msg(self, segment):
    #     self.enable_msg(segment, False)

    # def enable_msg(self, segment, enabled=True):
    #     # iterate over messages and enable the one for this segment
    #     for at in self.messages:
    #         msg = self.messages[at]
    #         if "segment" in msg and "enabled" in msg:
    #             if msg["segment"] == segment:
    #                 if isinstance(msg["msg"], str):
    #                     if msg["enabled"] != enabled:
    #                         msg["enabled"] = enabled
    #                         logging.debug(f"at {at}: {msg['msg']} enabled: {enabled}")

    def filter_from_topic(self, topic):
        frags = topic.split("/")
        driver = frags[1]
        session = frags[2]  # noqa
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
        if not self.history.ready:
            if self.history.error != self.previous_history_error:
                self.previous_history_error = self.history.error
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return self.history.error
            else:
                return None

        work_to_do = self.history.update(now, telemetry)
        if work_to_do and not self.history.threaded:
            self.history.do_work()

        if not self.messages:
            self.init_messages()

        distance_round_track = telemetry["DistanceRoundTrack"]
        if distance_round_track < self.previous_distance:
            self.messages = self.sort_messages(distance_round_track)
            self.previous_distance = distance_round_track

        next_message = self.messages[0]
        # FIXME: if distance is at the end of the track. -> modulo track_length
        distance = abs(next_message["at"] - distance_round_track)
        # print(distance)

        if distance < 10:
            self.messages.append(self.messages.pop(0))
            text_to_read = next_message.response()
            logging.debug(f"{distance_round_track:.1f}: {text_to_read}")
            return text_to_read

    def init_messages(self):
        self.track_length = self.history.track.length
        for segment in self.history.segments:
            if segment["mark"] == "brake":
                gear = ""
                if segment["gear"]:
                    gear = f"gear {segment['gear']} "
                text = gear + "%s percent" % (round(segment["force"] / 10) * 10)

                brake_msg = self.new_msg()
                # msg.segment = segment
                brake_msg.msg = text
                at = segment["start"]
                brake_msg.finish_at(at)

                brake_start_msg = self.new_msg()
                # msg.segment = segment
                features = segment.get("brake_features", {})
                brake_start_msg.at = features.get("start")
                brake_start_msg.msg = "brake"

                msg = self.new_msg()
                msg.at = brake_msg.at - 100
                msg.segment = segment
                msg.msg = self.eval_brake
                msg.related = [
                    brake_msg,
                    brake_start_msg,
                ]

            if segment["mark"] == "throttle":
                msg = self.new_msg()
                msg.segment = segment
                to = round(segment["force"] / 10) * 10
                msg.msg = "throttle to %s" % to
                msg.finish_at(segment["start"])

                msg = self.new_msg()
                msg.segment = segment
                features = segment.get("throttle_features", {})
                msg.at = features.get("start")
                msg.msg = "now"

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

    # def eval_gear(self, segment, **kwargs):
    #     gear = segment.gear
    #     if segment.gear != gear:
    #         self.enable_msg(segment)
    #     else:
    #         self.disable_msg(segment)

    def eval_brake(self, message):
        last_brake_start = message.segment.last_brake_features("start")
        coach_brake_start = message.segment.brake_features.get("start")
        brake_diff = last_brake_start - coach_brake_start
        logging.debug(f"eval_brake: brake_diff: {brake_diff:.1f} for turn {message.segment.turn}")

        if abs(brake_diff) < 10:
            for m in message.related:
                m.silence()
        else:
            for m in message.related:
                m.louden()
