from .application import Application

class TrackGuide(Application):

    def tick(self, telemetry):
        # gets called on every tick
        self.log("TrackGuide: notify")

        # return messages



