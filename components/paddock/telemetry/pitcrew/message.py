from .history import Segment
from .coach import Coach
from typing import Optional


class Message:
    coach: Coach
    segment: Optional[Segment]

    def __init__(self, coach: Coach, **kwargs):
        self.coach = coach
        self.segment = kwargs.get("segment")
        self.finish_at_words = "one two"
        self.at = None
        self.at_track_walk = None
        self.init()

    def log_debug(self, msg):
        self.coach.log_debug(msg)

    def init(self):
        pass

    def resp(self, distance, message, priority=9):
        # from CrewChiefV4.audio.SoundMetaData
        # this affects the queue insertion order. Higher priority items are inserted at the head of the queue
        # public int priority = DEFAULT_PRIORITY;  // 0 = lowest, 5 = default, 10 = spotter

        return {
            "distance": distance,
            "message": message,
            "priority": priority,
        }

    # One commonly used average reading speed for English is around 150 words per minute
    # when spoken. This translates to 2.5 words per second. So you can estimate the time
    # it takes to read a phrase out loud by counting the words and dividing by 2.5.
    # or check https://github.com/alanhamlett/readtime
    def read_time(self, msg=""):
        words = len(msg.split(" "))
        # r_time = words / 1.5
        r_time = words / 2.2
        delta_add = 1.5
        self.log_debug(f"read_time: '{msg}' ({words}) {r_time:.1f} seconds + {delta_add:.1f} seconds")
        # return words * 0.8  # avg ms per word
        # return words / 2.5  # avg ms per word
        return r_time + delta_add

    def finish_at(self, at=None, msg=""):
        msg = msg or self.msg
        at = at or self.at
        read_time = self.read_time(msg)
        respond_at = self.coach.history.offset_distance(at, seconds=read_time)
        return int(respond_at)

    def finish_at_segment_start(self, msg=""):
        msg = msg or self.msg
        at = self.segment.get("start")
        return self.finish_at(at)

    def needs_coaching(self):
        return True

    def response_hot_lap(self, distance, telemetry):
        if distance == self.at:
            if self.needs_coaching():
                return self.resp(self.at, self.msg)

    def response_track_walk(self, distance, telemetry):
        if distance == self.at_track_walk:
            return self.resp(self.at_track_walk, self.msg)

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
        self.diff_message_at = self.finish_at(self.at, self.message_earlier)
        self.at_track_walk = self.at - 100
        self.always_announce_brakepoint = True

    def response_track_walk(self, distance, telemetry):
        if distance == self.at_track_walk:
            return [
                self.resp(self.at_track_walk, self.msg_in_100, 9),
                # self.json_response(self.at_track_walk + 50, self.msg_in_50, 9),
                self.resp(self.at, self.msg, 9),
            ]

    def response_hot_lap(self, distance, telemetry):
        if distance == self.diff_message_at:
            if self.needs_coaching() or self.always_announce_brakepoint:
                messages = [self.resp(self.at, self.msg, 8)]
                if self.diff_message:
                    messages.append(self.resp(self.diff_message_at, self.diff_message, 8))
                return messages

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
        # self.force = self.segment.get("force")
        self.force = self.segment.brake_features.get("force")
        self.msg = "%s percent" % (round(int(self.force * 100) / 10) * 10)  # 0.73 -> 70
        # self.at = int(self.finish_at(self.segment.get("start")))
        self.at = self.finish_at_segment_start()
        self.at_track_walk = int(self.segment.brake_features.get("max_start"))

    def needs_coaching(self):
        # check brake force
        last_brake_force = self.segment.last_brake_features("force")
        if last_brake_force is None:
            self.log_debug("no last brake force")
            return True
        force_diff = last_brake_force - self.force
        force_diff_abs = abs(force_diff)
        self.log_debug(f"brake_force_diff: {force_diff:.2f} last: {last_brake_force:.2f} coach: {self.force:.2f}")
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
        self.log_debug(f"throttle_force_diff: {force_diff:.2f} last: {last_force:.2f} coach: {self.force:.2f}")
        if force_diff_abs > 0.3:
            # too much or too little
            return True
        #     new_fragments.append(force_fragment)
        # elif force_diff > 0.1:
        #     new_fragments.append("a bit less")
        # elif force_diff < -0.1:
        #     new_fragments.append("a bit harder")
