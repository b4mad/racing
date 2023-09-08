import django.utils.timezone

from telemetry.models import TrackGuide

from .application import Application


class DebugApplication(Application):
    def init(self):
        # get all notes for track and car
        self.track_guide = TrackGuide.objects.filter(car=self.session.car, track=self.session.track).first()
        if not self.track_guide:
            self.send_response("TrackGuide: no track guide found")
        else:
            self.send_response("TrackGuide found.")
        self.send_response("Starting debug app")
        self.send_response("I'll notify you on your average race pace percentage every 10 seconds")

        self.previous_pace_notification = django.utils.timezone.now()

    def tick(self):
        self.calculate_avg_speed()
        if (self.now - self.previous_pace_notification).seconds >= 10:
            pct = int(self.avg_speed_pct * 100)
            self.send_response(f"pace {pct} percent")
            self.previous_pace_notification = self.now

    def on_reset_to_pits(self):
        self.send_response("TrackGuide: on_reset_to_pits")

    def on_new_lap(self):
        self.send_response("TrackGuide: on_new_lap")
