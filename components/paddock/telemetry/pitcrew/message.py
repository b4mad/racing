from .segment import Segment


class Message:
    def __init__(self, segment: Segment, logger=None):
        self.segment = segment
        self.finish_at_words = "one two"
        self.at = None
        self.at_track_walk = None
        self.priority = 9
        self.logger = logger
        self.active = True
        self.init()

    def log_debug(self, msg):
        if self.logger:
            self.logger(msg)

    def init(self):
        pass

    def resp(self, distance, message, priority=None):
        # from CrewChiefV4.audio.SoundMetaData
        # this affects the queue insertion order. Higher priority items are inserted at the head of the queue
        # public int priority = DEFAULT_PRIORITY;  // 0 = lowest, 5 = default, 10 = spotter

        priority = priority or self.priority
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
        respond_at = self.segment.offset_distance(at, seconds=read_time)
        return int(respond_at)

    def finish_at_segment_start(self, msg=""):
        msg = msg or self.msg
        at = self.segment.start
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


class MessageBrake(Message):
    def init(self):
        self.msg = "brake"
        self.msg_in_100 = "brake in 100"
        self.msg_in_50 = "brake in 50"
        self.message_earlier = "brake a bit earlier"
        self.at = self.segment.brake_point()
        if self.at:
            self.common_init("brake")
        else:
            self.active = False

    def common_init(self, mark):
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
        # last_brake_start = self.segment.last_brake_features("start")
        last_brake_start = self.segment.avg_brake_start()
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
        self.at = self.segment.throttle_point()
        if self.at:
            self.common_init("throttle")
        else:
            self.active = False

    def needs_coaching(self):
        # check brake start
        # last_start = self.segment.last_throttle_features("start")
        last_start = self.segment.avg_throttle_start()
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
        self.gear = self.segment.gear()
        self.msg = f"Gear {self.gear}"
        self.at = self.finish_at_segment_start()
        self.priority = 7
        if self.segment.type_throttle():
            self.at_track_walk = self.segment.throttle_feature("end")
        elif self.segment.type_brake():
            self.at_track_walk = self.segment.brake_feature("end")
        if self.at_track_walk is not None:
            self.at_track_walk = self.at_track_walk - 30

    def needs_coaching(self):
        last_gear = self.segment.avg_gear()
        if last_gear is None:
            return True
        gear_diff = last_gear - self.gear
        self.log_debug(f"gear_diff: {gear_diff}")
        if abs(gear_diff) > 0.25:
            return True


class MessageBrakeForce(Message):
    def init(self):
        self.priority = 8
        self.force = self.segment.brake_force()
        if self.force is None or not self.segment.type_brake():
            self.active = False
            return
        self.msg = "%s percent" % (round(int(self.force * 100) / 10) * 10)  # 0.73 -> 70
        self.at = self.finish_at_segment_start()
        self.at_track_walk = self.segment.brake_point()

    def needs_coaching(self):
        # check brake force
        last_brake_force = self.segment.avg_brake_force()
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
        self.priority = 7
        self.force = self.segment.throttle_force()
        if self.force is None or not self.segment.type_throttle():
            self.active = False
            return
        self.force_pct = round(int(self.force * 100) / 10) * 10  # 0.73 -> 70
        self.msg = f"lift throttle to {self.force_pct} percent"
        self.at = self.finish_at_segment_start()
        self.at_track_walk = self.segment.throttle_point()

    def needs_coaching(self):
        # check brake force
        last_force = self.segment.avg_throttle_force()
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


class MessageApex(Message):
    def init(self):
        self.at = self.segment.apex()
        if self.at is not None:
            #     self.at = -1
            # else:
            self.at = self.at

        self.msg = "Apex"
        self.at = self.at
        self.at_track_walk = self.at

    def needs_coaching(self):
        return False
        # last_gear = self.segment.last_gear_features("gear")
        last = self.segment.avg_apex()
        if last is None:
            return True
        diff = last - self.at
        self.log_debug(f"apex_diff: {diff:.2f} last: {last:.2f} coach: {self.at:.2f}")

        if abs(diff) > 10:
            return True


class MessageTrailBrake(Message):
    def init(self):
        self.at = self.segment.trail_brake()
        self.msg = "trailbrake"
        self.at = self.at
        self.at_track_walk = self.at

    def needs_coaching(self):
        return False
        last = self.segment.avg_trail_brake()
        if last is None:
            return True
        diff = last - self.at
        self.log_debug(f"apex_diff: {diff:.2f} last: {last:.2f} coach: {self.at:.2f}")
        if abs(diff) > 10:
            return True
