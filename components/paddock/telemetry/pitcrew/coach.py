#!/usr/bin/env python3

import json
import logging
import django.utils.timezone
from .history import History
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Message:
    def __init__(self, history, **kwargs):
        self.history = history
        self.at = kwargs.get("at", 0)
        self.msg = kwargs.get("msg", "")
        self.segment = kwargs.get("segment", None)
        self.enabled = kwargs.get("enabled", True)
        self.json_respone = kwargs.get("json_respone", True)
        self.args = kwargs.get("args", [])
        self.kwargs = kwargs.get("kwargs", {})
        # self.track_length = kwargs.get("track_length", 0)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def response(self):
        if self.json_respone:
            return json.dumps(
                {
                    "message": self.msg,
                    "distance": self.at,
                    "priority": 9,
                }
            )
        return self.msg

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
        self.previous_distance = 0
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

    # def schedule_msg(self, at, msg, segment):
    #     message = self.new_msg(at=at, msg=msg, segment=segment)
    #     return message

    # def new_msg_done_by(self, at, msg, segment):
    #     message = self.new_msg(at=at, msg=msg, segment=segment)
    #     message.finish_at()
    #     return message

    # def schedule_msg_done_by(self, at, msg, segment):
    #     message = self.new_msg(at=at, msg=msg, segment=segment)
    #     message.finish_at()
    #     return message

    # def new_fn(self, at, fn, segment, **kwargs):
    #     message = self.new_msg(at=at, msg=fn, segment=segment)
    #     message["args"] = [segment]
    #     message["kwargs"] = kwargs
    #     return message

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

        self.history.update(now, telemetry)

        if not self.messages:
            self.init_messages()

        distance_round_track = telemetry["DistanceRoundTrack"]
        if distance_round_track < self.previous_distance:
            self.messages = self.sort_messages(distance_round_track)

        next_message = self.messages[0]
        # FIXME: if distance is at the end of the track. -> modulo track_length
        distance = abs(next_message["at"] - distance_round_track)
        # print(distance)

        if distance < 10:
            self.messages.append(self.messages.pop(0))
            # logging.debug(self.history.telemetry)
            return next_message.response()
            # msg = next_message["msg"]
            # if callable(msg):
            #     kwargs = next_message["kwargs"].copy()
            #     kwargs["telemetry"] = telemetry
            #     kwargs["at"] = next_message["at"]
            #     response = msg(*next_message["args"], **kwargs)
            #     if response:
            #         return response
            # elif isinstance(msg, dict):
            #     return json.dumps(msg)
            # else:
            #     return msg.response()

    def init_messages(self):
        self.track_length = self.history.track.length
        for segment in self.history.segments:
            if segment["mark"] == "brake":
                gear = ""
                if segment["gear"]:
                    gear = f"gear {segment['gear']} "
                text = gear + "%s percent" % (round(segment["force"] / 10) * 10)

                msg = self.new_msg()
                # msg.segment = segment
                msg.msg = text
                at = segment["start"]
                msg.finish_at(at)

                msg = self.new_msg()
                # msg.segment = segment
                features = self.history.features(segment)
                msg.at = features.get("start")
                msg.msg = "brake"

                # at = segment.end + 20
                # self.new_fn(at, self.eval_brake, segment, brake_msg_at=msg["at"])

            if segment["mark"] == "throttle":
                msg = self.new_msg()
                # msg.segment = segment
                to = round(segment["force"] / 10) * 10
                msg.msg = "throttle to %s" % to
                msg.finish_at(segment["start"])

                msg = self.new_msg()
                msg.segment = segment
                features = self.history.features(segment, mark="throttle")
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

    # def eval_brake(self, segment, **kwargs):
    #     # driver_brake_start = self.history.driver_brake(segment)
    #     meters = kwargs["telemetry"]["DistanceRoundTrack"]
    #     driver_brake_start = self.history.t_start_distance(segment.start - 50, segment.end, "Brake")
    #     delta = driver_brake_start - segment.start
    #     time_segment_at = self.history.t_at_distance(segment.start, "CurrentLapTime")
    #     time_driver_brake_start = self.history.t_at_distance(driver_brake_start, "CurrentLapTime")
    #     # time_delta = time_brake_msg_at - time_driver_brake_start
    #     time_delta = time_driver_brake_start - time_segment_at
    #     speed = self.history.t_at_distance(driver_brake_start, "SpeedMs")
