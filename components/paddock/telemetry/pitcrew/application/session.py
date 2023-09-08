from telemetry.models import Car, Game, SessionType, Track


class Session:
    def __init__(self):
        self.id = ""
        self.track = Track()
        self.car = Car()
        self.game = Game()
        self.session_type = SessionType()

    def track_length(self) -> float:
        return self.track.length
