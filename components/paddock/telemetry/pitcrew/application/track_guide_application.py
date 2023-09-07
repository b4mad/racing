from telemetry.models import TrackGuide

from .application import Application


class TrackGuideApplication(Application):
    def init(self):
        self.log("TrackGuide: init")

        # get all notes for track and car
        self.track_guide = TrackGuide.objects.filter(car=self.session.car, track=self.session.track).first()
        if not self.track_guide:
            self.send_response("TrackGuide: no track guide found")

    def tick(self, distance: int):
        # gets called on every tick
        # return messages
        pass
