import datetime
from collections import deque

from telemetry.pitcrew.history import History
from telemetry.pitcrew.logging import LoggingMixin

from .response import Response, ResponseInstant
from .session import Session


class Application(LoggingMixin):
    def __init__(self, session: Session, history: History, coach):
        self.session = session
        self.session_id = session.id
        self.responses = []
        self.history = history
        self.coach = coach
        self.distance = -1
        self.speed_pct_history = deque(maxlen=500)
        self.speed_pct_sum = 0.0
        self.avg_speed_pct = 0
        self.segments_by_turn = {}
        for segment in self.history.segments:
            self.segments_by_turn[segment.turn] = segment
        self.init()

    def notify(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.telemetry = telemetry
        self.distance = distance
        self.speed = telemetry["SpeedMs"]
        self.now = now
        self.tick()

    def yield_responses(self):
        # return messages
        for response in self.responses:
            yield response

        self.responses = []

    def distance_add(self, distance, meters):
        return (distance + meters) % self.session.track_length()

    def message_playing_at(self, distance):
        return self.coach.message_playing_at(distance)

    def get_segment(self, turn):
        return self.segments_by_turn[turn]

    def finish_at(self, at, response):
        read_time = response.read_time()
        respond_at = self.history.distance_add(at, seconds=-1 * read_time)
        return int(respond_at)

    def max_distance_delta(self, segment):
        approach_speed = segment.approach_speed()
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

    def send_response(self, message, priority=5, max_distance=None, max_distance_delta=None, at=None, finish_at=None):
        # from CrewChiefV4.audio.SoundMetaData
        # this affects the queue insertion order. Higher priority items are inserted at the head of the queue
        # public int priority = DEFAULT_PRIORITY;  // 0 = lowest, 5 = default, 10 = spotter
        if at is None and finish_at is None:
            response = ResponseInstant(message, priority=priority)
        else:
            distance = at or finish_at
            response = Response(message, priority=priority, at=distance)
            if finish_at:
                response.at = self.finish_at(finish_at, response)

        if max_distance_delta:
            response.max_distance = self.distance_add(response.at, max_distance_delta)

        self.responses.append(response)
        return response

    def race_pace_speed_at(self, distance):
        return self.history.map_distance_speed.get(distance, 0)

    def calculate_avg_speed(self):
        race_pace_speed = self.race_pace_speed_at(self.distance)
        if race_pace_speed:
            speed_pct = self.speed / race_pace_speed
            # Add current speed pct to history
            if len(self.speed_pct_history) == self.speed_pct_history.maxlen:
                # Remove the oldest value from the sum
                self.speed_pct_sum -= self.speed_pct_history[0]
            self.speed_pct_history.append(speed_pct)
            # Add the new value to the sum
            self.speed_pct_sum += speed_pct

            self.avg_speed_pct = self.speed_pct_sum / len(self.speed_pct_history)

    def eval_at(self, snippet, segment):
        globals = {
            "brake_point": segment.brake_point,
            "apex": segment.apex,
            "gear": segment.gear_distance,
            "turn_in": segment.turn_in,
        }
        return self.eval(snippet, segment, globals)

    def eval(self, snippet, segment, globals=None):
        globals = globals or {
            "segment": segment,
            "brake_point": segment.brake_point,
            "apex": segment.apex,
            "brake_point_diff": segment.brake_point_diff,
            "apex_diff": segment.apex_diff,
            "gear_diff": segment.gear_diff,
            "coach_brake_force": segment.coach_brake_force,
            "coach_turn_in": segment.coach_turn_in,
            "coach_brake_point": segment.coach_brake_point,
            "coach_gear": segment.coach_gear,
            "coach_apex": segment.coach_apex,
            "coach_throttle_force": segment.coach_throttle_force,
        }
        try:
            rv = eval(snippet, globals)  # nosec
            self.log_debug(f"eval: {snippet} -> {rv}")
            return rv
        except Exception as e:
            error = f"eval error: {snippet} -> {e}"
            self.log_debug(error)
            return error

    def segments_for_landmark(self, landmark):
        segments = []
        for segment in self.history.segments:
            if segment.start <= landmark.start <= segment.end:
                segments.append(segment)
            if segment.start <= landmark.end <= segment.end:
                segments.append(segment)
        return segments

    def init(self):
        pass

    def tick(self):
        # get's called by super class
        pass

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass

    def on_crash(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass
