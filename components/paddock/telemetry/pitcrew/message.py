from telemetry.pitcrew.logging import LoggingMixin
from .history import Segment
from .coach import Coach
from typing import Optional


class Message(LoggingMixin):
    coach: Coach
    segment: Optional[Segment]

    def __init__(self, coach: Coach, **kwargs):
        self.coach = coach
        self.segment = kwargs.get("segment")
        self.finish_at_words = "one two"
        self.at = None
        self.at_track_walk = None
        self.init()

    def __getattr__(self, key):
        if key == "session_id":
            return self.coach.session_id
        return getattr(self, key)

    def init(self):
        pass

    def json_response(self, distance, message, priority=9):
        return {
            "distance": distance,
            "message": message,
            "priority": priority,
        }

    def read_time(self, msg=""):
        words = len(msg.split(" "))
        return words * 0.8  # avg ms per word

    def finish_at(self, at=None, msg=""):
        msg = msg or self.msg
        at = at or self.at
        read_time = self.read_time(msg)
        respond_at = self.coach.history.offset_distance(at, seconds=read_time)
        return int(respond_at)

    def finish_at_segment_start(self):
        at = self.segment.get("start")
        return self.finish_at(at, self.finish_at_words)

    def needs_coaching(self):
        return True

    def response_hot_lap(self, distance, telemetry):
        if distance == self.at:
            if self.needs_coaching():
                return self.json_response(self.at, self.msg)

    def response_track_walk(self, distance, telemetry):
        if distance == self.at_track_walk:
            return self.json_response(self.at_track_walk, self.msg)

    def response(self, distance, telemetry):
        if self.coach.track_walk:
            return self.response_track_walk(distance, telemetry)
        else:
            return self.response_hot_lap(distance, telemetry)


class MessageBrake(Message):
    def init(self):
        self.msg = "brake"
        self.msg_in_100 = "brake in 100"
        self.msg_in_50 = "brake in 50"
        self.message_earlier = "brake a bit earlier"
        self.common_init("brake")

    def common_init(self, mark):
        self.at = int(self.segment.features("start", mark=mark))
        self.diff_message = ""
        self.diff_message_at = self.finish_at_segment_start()
        self.at_track_walk = self.at - 100

    def response_track_walk(self, distance, telemetry):
        if distance == self.at_track_walk:
            return [
                self.json_response(self.at_track_walk, self.msg_in_100, 9),
                # self.json_response(self.at_track_walk + 50, self.msg_in_50, 9),
                self.json_response(self.at, self.msg, 9),
            ]

    def response_hot_lap(self, distance, telemetry):
        if distance == self.diff_message_at:
            if self.needs_coaching():
                return [
                    self.json_response(self.diff_message_at, self.diff_message, 8),
                    self.json_response(self.at, self.msg, 8),
                ]

    def needs_coaching(self):
        # check brake start
        last_brake_start = self.segment.last_brake_features("start")
        if last_brake_start is None:
            return True
        brake_diff = last_brake_start - self.at
        # brake_diff_abs = abs(brake_diff)
        self.log_debug(f"brake_diff: {brake_diff:.1f}")

        self.diff_message = ""
        if brake_diff > 20:
            # too late
            self.diff_message = self.message_earlier
        elif brake_diff < -20:
            # too early
            self.diff_message = "brake a bit later"

        return bool(self.diff_message)


class MessageThrottle(MessageBrake):
    def init(self):
        self.msg = "lift"
        self.msg_in_100 = "lift throttle in 100 meters"
        self.msg_in_50 = "in 50"
        self.message_earlier = "lift a bit earlier"
        self.common_init("throttle")

    def needs_coaching(self):
        # check brake start
        last_start = self.segment.last_throttle_features("start")
        if last_start is None:
            last_start = 100_000_000
        throttle_diff = last_start - self.at
        diff_abs = abs(throttle_diff)
        self.log_debug(f"throttle_diff: {throttle_diff:.1f}")

        self.diff_message = ""
        if diff_abs > 50:
            self.diff_message = "lift throttle"
        elif throttle_diff > 20:
            # too late
            self.diff_message = self.message_earlier
        elif throttle_diff < -20:
            # too early
            self.diff_message = "lift a bit later"

        return bool(self.diff_message)


class MessageGear(Message):
    def init(self):
        self.gear = self.segment.get("gear")
        self.msg = f"Gear {self.gear}"
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()
        if self.segment["mark"] == "throttle":
            self.at_track_walk = self.segment.throttle_features.get("end")
        elif self.segment["mark"] == "brake":
            self.at_track_walk = self.segment.brake_features.get("end")
        if self.at_track_walk is not None:
            self.at_track_walk = int(self.at_track_walk - 30)

    def needs_coaching(self):
        last_gear = self.segment.last_gear_features("gear")
        if last_gear is None:
            return True
        gear_diff = last_gear - self.gear
        self.log_debug(f"gear_diff: {gear_diff}")
        if gear_diff != 0:
            return True


class MessageBrakeForce(Message):
    def init(self):
        self.force = self.segment.get("force")
        self.msg = "%s percent" % (round(self.force / 10) * 10)
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()
        self.at_track_walk = int(self.segment.brake_features.get("max_start"))

    def needs_coaching(self):
        # check brake force
        last_brake_force = self.segment.last_brake_features("force")
        if last_brake_force is None:
            return True
        force_diff = last_brake_force - self.force
        force_diff_abs = abs(force_diff)
        self.log_debug(f"force_diff: {force_diff:.2f}")
        if force_diff_abs > 0.3:
            # too much or too little
            return True
        #     new_fragments.append(force_fragment)
        # elif force_diff > 0.1:
        #     new_fragments.append("a bit less")
        # elif force_diff < -0.1:
        #     new_fragments.append("a bit harder")


class MessageThrottleForce(Message):
    def init(self):
        self.force = self.segment.get("force")
        self.msg = "lift throttle to %s percent" % (round(self.force / 10) * 10)
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()
        self.at_track_walk = int(self.segment.throttle_features.get("max_start"))

    def needs_coaching(self):
        # check brake force
        last_force = self.segment.last_throttle_features("force")
        if last_force is None:
            return True
        force_diff = last_force - self.force
        force_diff_abs = abs(force_diff)
        self.log_debug(f"force_diff: {force_diff:.2f}")
        if force_diff_abs > 0.3:
            # too much or too little
            return True
        #     new_fragments.append(force_fragment)
        # elif force_diff > 0.1:
        #     new_fragments.append("a bit less")
        # elif force_diff < -0.1:
        #     new_fragments.append("a bit harder")
