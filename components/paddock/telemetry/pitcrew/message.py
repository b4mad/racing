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
        self.five_words = "one two three four five"
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
        return self.finish_at(at, self.five_words)

    def needs_coaching(self):
        return True

    def response(self, distance, telemetry):
        if distance == self.at:
            if self.needs_coaching():
                return self.json_response(self.at, self.msg)


class MessageBrake(Message):
    def init(self):
        self.at = int(self.segment.brake_features.get("start"))
        self.msg = "brake"
        self.brake_diff_message = ""
        self.message_earlier = "brake a bit earlier"
        # self.brake_diff_message_at = self.finish_at(self.at, self.message_earlier)
        self.brake_diff_message_at = self.finish_at_segment_start()

    def needs_coaching(self):
        # check brake start
        last_brake_start = self.segment.last_brake_features("start")
        if last_brake_start is None:
            return True
        brake_diff = last_brake_start - self.at
        # brake_diff_abs = abs(brake_diff)
        self.log_debug(f"brake_diff: {brake_diff:.1f}")

        self.brake_diff_message = ""
        if brake_diff > 20:
            # too late
            self.brake_diff_message = self.message_earlier
        elif brake_diff < -20:
            # too early
            self.brake_diff_message = "brake a bit later"

        return bool(self.brake_diff_message)

    def response(self, distance, telemetry):
        if distance == self.brake_diff_message_at:
            if self.needs_coaching():
                return [
                    self.json_response(self.brake_diff_message_at, self.brake_diff_message, 8),
                    self.json_response(self.at, self.msg, 8),
                ]


class MessageGear(Message):
    def init(self):
        self.gear = self.segment.get("gear")
        self.msg = f"Gear {self.gear}"
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()

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


class MessageThrottle(Message):
    def init(self):
        self.at = int(self.segment.throttle_features.get("start"))
        self.msg = "lift"
        self.diff_message = ""
        self.message_earlier = "lift a bit earlier"
        # self.brake_diff_message_at = self.finish_at(self.at, self.message_earlier)
        self.diff_message_at = self.finish_at_segment_start()

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

    def response(self, distance, telemetry):
        if distance == self.diff_message_at:
            if self.needs_coaching():
                return [
                    self.json_response(self.diff_message_at, self.diff_message, 8),
                    self.json_response(self.at, self.msg, 8),
                ]


class MessageThrottleForce(Message):
    def init(self):
        self.force = self.segment.get("force")
        self.msg = "lift throttle to %s percent" % (round(self.force / 10) * 10)
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()

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
