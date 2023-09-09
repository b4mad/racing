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
        self.init()

    def notify(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.telemetry = telemetry
        self.distance = distance
        self.speed = telemetry["SpeedMs"]
        self.now = now
        self.tick()

        # return messages
        for response in self.responses:
            yield response

        self.responses = []

    def distance_add(self, meters):
        return (self.distance + meters) % self.session.track_length()

    def message_playing_at(self, distance):
        return self.coach.message_playing_at(distance)

    def get_segment(self, turn):
        pass

    def send_response(self, message, priority=5, max_distance=None, at=None):
        # from CrewChiefV4.audio.SoundMetaData
        # this affects the queue insertion order. Higher priority items are inserted at the head of the queue
        # public int priority = DEFAULT_PRIORITY;  // 0 = lowest, 5 = default, 10 = spotter
        if at is None:
            response = ResponseInstant(message, priority=priority)
        else:
            response = Response(message, priority=priority, at=at)

        self.responses.append(response)

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

    def init(self):
        pass

    def tick(self):
        # get's called by super class
        pass

    def on_session_start(self):
        pass
