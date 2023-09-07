from .response import Response, ResponseInstant
from .session import Session


class Application:
    def __init__(self, session: Session):
        self.session = session
        self.responses = []
        self.init()

    def log(self, message):
        pass

    def notify(self, distance: int, telemetry: dict):
        self.telemetry = telemetry
        self.tick(distance)

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

    def init(self):
        pass

    def tick(self, distance: int):
        # get's called by super class
        pass

    def on_session_start(self):
        pass
