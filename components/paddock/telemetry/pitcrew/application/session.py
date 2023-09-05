from telemetry.models import Track


class Session:
    def __init__(self):
        self.id = ""
        self.track = Track()

    def track_length(self) -> float:
        return self.track.length
