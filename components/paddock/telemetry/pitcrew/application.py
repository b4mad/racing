class Application():
    def __init__(self, session=None):
        self.session = session

    def log(self, message):
        pass

    def notify(self, telemetry={}):
        # gets called on every tick
        self.log.info("TrackGuide: notify")

        self.tick(telemetry)

        # return messages
        for message in self.messages:
            yield message

    def tick(self, telemetry):
        # get's called by super class
        # noop
        pass

    def send_message(self, message):
        self.messages.append(message)


