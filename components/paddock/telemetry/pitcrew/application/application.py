from telemetry.pitcrew.history import History
from telemetry.pitcrew.logging import LoggingMixin

from .response import Response, ResponseInstant
from .session import Session


class Application(LoggingMixin):
    def __init__(self, session: Session, history: History):
        self.session = session
        self.session_id = session.id
        self.responses = []
        self.history = history
        self.distance = -1
        self.init()

    def notify(self, distance: int, telemetry: dict):
        self.telemetry = telemetry
        self.distance = distance
        self.speed = telemetry["SpeedMs"]
        self.tick()

        # return messages
        for response in self.responses:
            yield response

        self.responses = []

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

    def init(self):
        pass

    def tick(self):
        # get's called by super class
        pass

    def on_session_start(self):
        pass
