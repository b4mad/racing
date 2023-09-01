from telemetry.models import Coach

from .segment import Segment


class Message:
    def __init__(self, segment: Segment, logger=None, mode="hotlap"):
        self.segment = None
        self.segments = []
        self.add_segment(segment)

        self.finish_at_words = "one two"
        self.at = None
        self.at_track_walk = None
        self.priority = 9
        self.logger = logger
        self.active = True
        self.mode = mode
        self.msg = ""
        self.init()
        self.max_distance = None
        if self.at is not None:
            self.max_distance = self.at + self.max_distance_delta()

    def add_segment(self, segment):
        if segment:
            if self.segment is None:
                self.segment = segment
                self.segments.append(segment)
            else:
                self.segments.append(segment)

    def log_debug(self, msg):
        if self.logger:
            self.logger(msg)

    def init(self):
        pass

    def resp(self, distance, message, priority=None, max_distance=None):
        # from CrewChiefV4.audio.SoundMetaData
        # this affects the queue insertion order. Higher priority items are inserted at the head of the queue
        # public int priority = DEFAULT_PRIORITY;  // 0 = lowest, 5 = default, 10 = spotter

        priority = priority or self.priority
        response = {"distance": distance, "message": message, "priority": priority}
        if max_distance or self.max_distance:
            r_max_distance = max_distance or self.max_distance
            response["max_distance"] = r_max_distance
        return response

    # One commonly used average reading speed for English is around 150 words per minute
    # when spoken. This translates to 2.5 words per second. So you can estimate the time
    # it takes to read a phrase out loud by counting the words and dividing by 2.5.
    # or check https://github.com/alanhamlett/readtime
    def read_time(self, msg=""):
        words = len(msg.split(" "))
        # r_time = words / 1.5
        r_time = words / 2.2
        # delta_add = 2.0
        delta_add = 0.2
        self.log_debug(f"read_time: '{msg}' ({words}) {r_time:.1f} seconds + {delta_add:.1f} seconds")
        # return words * 0.8  # avg ms per word
        # return words / 2.5  # avg ms per word
        return r_time + delta_add

    def finish_at(self, at=None, msg=""):
        msg = msg or self.msg
        if at is None:
            at = self.at
        read_time = self.read_time(msg)
        respond_at = self.segment.offset_distance(at, seconds=read_time)
        self.max_distance = respond_at + self.max_distance_delta()
        return int(respond_at)

    def finish_at_segment_start(self, msg=""):
        msg = msg or self.msg
        at = self.segment.start
        return self.finish_at(at)

    def max_distance_delta(self):
        approach_speed = self.segment.approach_speed()
        if approach_speed is None:
            return 10

        # The formula for the slope of a line when you have two points
        # (x1, y1) and (x2, y2) is m = (y2 - y1) / (x2 - x1).
        # So the slope m for your points (30,10) and (60,15) is (15-10) / (60-30) = 5 / 30 = 1/6.
        # Then, once we have the slope, we can find the y-intercept, b,
        # using the equation b = y - mx, using one of our points.
        # I will use the point (30,10): b = 10 - (1/6)*30 = 10 - 5 = 5
        # So the equation of the line that goes through these two points is:
        # y = (1/6)x + 5

        slope = 1 / 6
        intercept = 7

        max_distance = slope * approach_speed + intercept
        self.log_debug(f"max_distance: {max_distance:.1f} approach_speed: {approach_speed:.1f}")
        return int(max_distance)

    def needs_coaching(self):
        return True

    def response_hot_lap(self, distance, telemetry):
        if distance == self.at:
            if self.needs_coaching():
                return self.resp(self.at, self.msg)

    def response_track_walk(self, distance, telemetry):
        if distance == self.at_track_walk:
            return self.resp(self.at_track_walk, self.msg)


class MessageBrakePoint(Message):
    def init(self):
        self.msg = "brake"
        # if self.mode == Coach.MODE_DEBUG or self.mode == Coach.MODE_ONLY_BRAKE_DEBUG:
        #     self.msg = f"brake {self.segment.turn}"

        self.active = self.segment.type_brake()
        self.at = self.segment.brake_point()
        # if self.at is not None:
        #     self.max_distance = self.at + 100
        self.priority = 9

    def needs_coaching(self):
        # always announce
        return True


class MessageThrottlePoint(Message):
    def init(self):
        self.msg = "lift"
        # if self.mode == Coach.MODE_DEBUG or self.mode == Coach.MODE_ONLY_BRAKE_DEBUG:
        #     self.msg = f"lift {self.segment.turn}"

        self.active = self.segment.type_throttle()
        self.at = self.segment.throttle_point()
        # if self.at is not None:
        #     self.max_distance = self.at + 100
        self.priority = 9

    def needs_coaching(self):
        # always announce
        return True


class MessageBrake(Message):
    def init(self):
        self.msg = ""
        self.msg_in_100 = "brake in 100"
        self.msg_in_50 = "brake in 50"
        self.message_earlier = "brake a bit earlier"
        self.at = self.segment.brake_point()
        self.active = self.segment.type_brake()
        self.priority = 9

    # def common_init(self, mark):
    #     self.at_track_walk = self.at - 100

    # def response_track_walk(self, distance, telemetry):
    #     if distance == self.at_track_walk:
    #         return [
    #             self.resp(self.at_track_walk, self.msg_in_100, 9),
    #             # self.json_response(self.at_track_walk + 50, self.msg_in_50, 9),
    #         ]

    # def response_hot_lap(self, distance, telemetry):
    #     if distance == self.at:
    #         if self.needs_coaching():
    #             # messages = [self.resp(self.at, self.msg, 8)]
    #             messages = []
    #             if self.diff_message:
    #                 messages.append(self.resp(self.diff_message_at, self.diff_message, 8))
    #             return messages

    def needs_coaching(self):
        if self.segment.driver_score() < 0.5:
            return False

        last_brake_start = self.segment.avg_brake_start()
        if last_brake_start is None:
            return True
        brake_diff = last_brake_start - self.at
        # brake_diff_abs = abs(brake_diff)
        self.log_debug(f"brake_diff: {brake_diff:.1f}")

        diff_message = ""
        if brake_diff > 20:
            # too late
            diff_message = self.message_earlier
        elif brake_diff < -20:
            # too early
            diff_message = "brake a bit later"

        self.msg = diff_message
        self.at = self.finish_at_segment_start()

        return bool(self.msg)


class MessageThrottle(Message):
    def init(self):
        self.msg = ""
        self.msg_in_100 = "lift throttle in 100 meters"
        self.msg_in_50 = "in 50"
        self.message_earlier = "lift a bit earlier"
        self.at = self.segment.throttle_point()
        self.active = self.segment.type_throttle()

    def needs_coaching(self):
        if self.segment.driver_score() < 0.5:
            return False

        last_start = self.segment.avg_throttle_start()
        if last_start is None:
            last_start = 100_000_000
        throttle_diff = last_start - self.at
        diff_abs = abs(throttle_diff)
        self.log_debug(f"throttle_diff: {throttle_diff:.1f}")

        diff_message = ""
        if diff_abs > 50:
            diff_message = "lift throttle"
        elif throttle_diff > 20:
            # too late
            diff_message = self.message_earlier
        elif throttle_diff < -20:
            # too early
            diff_message = "lift a bit later"

        self.msg = diff_message
        self.at = self.finish_at_segment_start()

        return bool(self.msg)


class MessageGear(Message):
    def init(self):
        self.gear = self.segment.gear()
        self.msg = f"Gear {self.gear}"
        self.at = self.finish_at_segment_start()
        self.priority = 9
        if self.segment.type_throttle():
            self.at_track_walk = self.segment.throttle_feature("end")
        elif self.segment.type_brake():
            self.at_track_walk = self.segment.brake_feature("end")
        if self.at_track_walk is not None:
            self.at_track_walk = self.at_track_walk - 30

    def needs_coaching(self):
        if self.segment.driver_score() < 0.5:
            return False

        last_gear = self.segment.avg_gear()
        if last_gear is None:
            return True
        gear_diff = last_gear - self.gear
        self.log_debug(f"gear_diff: {gear_diff}")
        if abs(gear_diff) > 0.25:
            return True


class MessageBrakeForce(Message):
    def init(self):
        self.priority = 9
        self.force = self.segment.brake_force()
        if self.force is None or not self.segment.type_brake():
            self.active = False
            return
        self.msg = "%s percent" % (round(int(self.force * 100) / 10) * 10)  # 0.73 -> 70
        self.at = self.finish_at_segment_start()
        self.at_track_walk = self.segment.brake_point()

    def needs_coaching(self):
        if self.segment.driver_score() < 0.5:
            return False

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
        self.priority = 9
        self.force = self.segment.throttle_force()
        if self.force is None or not self.segment.type_throttle():
            self.active = False
            return
        self.force_pct = round(int(self.force * 100) / 10) * 10  # 0.73 -> 70
        self.msg = f"lift throttle to {self.force_pct} percent"
        self.at = self.finish_at_segment_start()
        self.at_track_walk = self.segment.throttle_point()

    def needs_coaching(self):
        if self.segment.driver_score() < 0.5:
            return False

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
        self.at = self.segment.brake_feature("max_end")
        if self.at is not None:
            self.at = int(self.at)
        self.msg = "trailbrake"
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


class MessageTrackGuide(Message):
    def init(self):
        self.msg = self.build_msg()
        # self.at = self.segment.previous_segment.full_throttle_point()
        # if self.at is not None:
        #     diff = (self.segment.brake_point() - self.at) % self.segment.track_length()
        finish_at = self.segment.brake_point() or self.segment.throttle_point() or self.segment.start
        self.at = self.finish_at(finish_at)
        # self.msg = f"{self.msg} {self.segment.start}"
        self.at_track_walk = self.at
        # self.max_distance = self.at + 15

    def build_msg(self):
        brake_point = self.segment.brake_point()
        throttle_point = self.segment.throttle_point()
        frags = []
        if brake_point is None:
            if throttle_point is not None:
                frags.append("lift throttle")
                if self.segment.throttle_force() > 0.3:
                    frags.append("a bit")

        else:
            brake_force = self.segment.brake_force()
            if brake_force > 0.65:
                # Heavy braking
                frags.append("brake hard")
            elif brake_force > 0.3:
                frags.append("brake normal")
                # Medium braking
            else:
                frags.append("touch the brake")
                # Light braking
        if self.segment.trail_brake():
            frags.append("trailbrake")

        # fixme compare to gear at start of segment
        frags.append(f"gear {self.segment.gear()}")
        return " ".join(frags)

    def needs_coaching(self):
        if self.mode == Coach.MODE_DEBUG:
            return True

        if self.segment.driver_score() < 0.5:
            return True
        return False


class MessageFocus(Message):
    def init(self):
        self.msg = self.build_msg()
        at = self.finish_at_segment_start()
        self.at = self.segment.offset_distance(at, seconds=4)

    def build_msg(self):
        return "focus on the next turn"

    def needs_coaching(self):
        return False


class MessageTrackGuideNotes(Message):
    def init(self):
        self.notes = []
        self.current_note = None
        self.current_note_index = 0
        self.note_play_counter = {}
        self.note_scores = {}

    def response_hot_lap(self, distance, telemetry):
        # at the start of the previous segment score all notes
        if distance == self.segment.previous_segment.start:
            self.score_notes()

        if distance == self.at:
            # increase note play counter
            self.note_play_counter[self.current_note] += 1
            return self.resp(self.at, self.msg)

    def score_notes(self):
        # score every note
        score_logs = []
        for note in self.notes:
            # 0 = lowest, 1 = highest
            if note.score.strip() == "":
                score = 0.5
            else:
                score = float(self.eval_score(note.score))
            if score is None or score == 0.0:
                self.log_debug(f"score is {score} -> 0.1: {note}")
                score = 0.1
            priority = note.priority or 1
            counter = self.note_play_counter[note]
            final_score = (1 / score) * priority * (1 / counter)
            self.note_scores[note] = final_score
            score_logs.append(f"{final_score:02.2f} - s: {score:.2f} p: {priority} c: {counter} - {note}")

        # find the highest score
        highest_score = -1
        lowest_play_counter = 1
        for note, score in self.note_scores.items():
            if score > highest_score:
                highest_score = score
                lowest_play_counter = self.note_play_counter[note]
                self.current_note = note
            elif score == highest_score:
                if self.note_play_counter[note] < lowest_play_counter:
                    lowest_play_counter = self.note_play_counter[note]
                    self.current_note = note

        # set at and build message
        self.build_msg()

        [self.log_debug(log) for log in score_logs]
        self.log_debug(f"segment {self.current_note.segment}: s: {highest_score:02.2f} : at {self.at}: {self.msg}")

    def set_notes(self, notes, mode="segment"):
        if mode == "segment":
            self.brake_or_throttle_point = self.segment.brake_point() or self.segment.throttle_point()
        elif mode == "landmark":
            self.landmark = notes[0].landmark
            self.brake_or_throttle_point = self.landmark.start
        self.eval_notes = {}
        self.notes = []
        for note in notes:
            if note.ref_eval:
                if note.ref_eval not in self.eval_notes:
                    self.eval_notes[note.ref_id] = []
                self.eval_notes[note.ref_id].append(note)
            else:
                self.notes.append(note)
                self.note_play_counter[note] = 1

        # sort notes by priority
        self.notes.sort(key=lambda x: x.priority)

        self.current_note = self.notes[0]
        self.build_msg()

    # def next_note(self):
    #     if self.current_note_index == len(self.notes) - 1:
    #         return self.current_note
    #     else:
    #         self.current_note_index += 1
    #     nn = self.notes[self.current_note_index]
    #     if len(nn.eval.strip()) == 0:
    #         return self.next_note()
    #     return nn

    def build_msg(self, msg=None):
        self.msg = msg or self.current_note.message
        evaluated = False
        if self.current_note.at_start:
            evaluated = "at"
            at = self.eval_at(self.current_note.at_start)
        elif self.current_note.at:
            evaluated = "finish_at"
            at = self.eval_at(self.current_note.at)
        else:
            self.at = self.finish_at(self.brake_or_throttle_point)

        if evaluated:
            if type(at) is str and at.isnumeric():
                at = int(at)
            if type(at) is int or type(at) is float:
                at = int(at)
            if type(at) is int:
                if evaluated == "finish_at":
                    at = self.finish_at(at)
                else:
                    self.max_distance = at + self.max_distance_delta()
                self.at = at
            else:
                self.msg = f"{at}"
                self.log_debug(f"eval at error: {self.msg}")

    # def needs_coaching(self):
    #     # eval current note
    #     rv = self.eval(self.current_note.eval)
    #     if type(rv) is str:
    #         self.build_msg(rv)
    #     else:
    #         self.build_msg()
    #     if rv:
    #         self.current_note = self.next_note()

    #     return True

    def eval_score(self, snippet):
        globals = {
            "brake_point": self.segment.score_brake_point,
            "apex": self.segment.score_apex,
            "gear": self.segment.score_gear,
            "brake_force": self.segment.score_brake_force,
            "turn_in": self.segment.score_turn_in,
            "throttle_force": self.segment.score_throttle_force,
        }
        return self.eval(snippet, globals)

    def eval_at(self, snippet):
        globals = {
            "brake_point": self.segment.brake_point,
            "apex": self.segment.apex,
            "gear": self.segment.gear_distance,
            "turn_in": self.segment.turn_in,
        }
        return self.eval(snippet, globals)

    def eval(self, snippet, globals=None):
        globals = globals or {
            "segment": self.segment,
            "brake_point": self.segment.brake_point,
            "apex": self.segment.apex,
            "brake_point_diff": self.segment.brake_point_diff,
            "apex_diff": self.segment.apex_diff,
            "gear_diff": self.segment.gear_diff,
            "coach_brake_force": self.segment.coach_brake_force,
            "coach_turn_in": self.segment.coach_turn_in,
            "coach_brake_point": self.segment.coach_brake_point,
            "coach_gear": self.segment.coach_gear,
            "coach_apex": self.segment.coach_apex,
            "coach_throttle_force": self.segment.coach_throttle_force,
        }
        try:
            rv = eval(snippet, globals)  # nosec
            self.log_debug(f"eval: {snippet} -> {rv}")
            return rv
        except Exception as e:
            error = f"eval error: {snippet} -> {e}"
            self.log_debug(error)
            return error
