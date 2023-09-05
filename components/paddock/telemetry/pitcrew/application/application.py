from .session import Session


class Application:
    def __init__(self, session: Session):
        self.session = session
        self.messages = []

    def log(self, message):
        pass

    def notify(self, distance: int, telemetry: dict):
        self.telemetry = telemetry
        self.tick(distance)

        # return messages
        for message in self.messages:
            yield message

    def tick(self, distance: int):
        # get's called by super class
        pass

    def send_message(self, message):
        self.messages.append(message)
