import datetime

import django.utils.timezone

from .application import Application


class DebugApplication(Application):
    def init(self):
        self.send_response("Starting debug app")
        self.send_response("I'll notify you on your average race pace percentage every 10 seconds")

        self.previous_pace_notification = django.utils.timezone.now()

    def tick(self):
        self.calculate_avg_speed()
        if (self.now - self.previous_pace_notification).seconds >= 10:
            pct = int(self.avg_speed_pct * 100)
            self.send_response(f"pace {pct} percent")
            self.previous_pace_notification = self.now

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("Debug Reset to pits")

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("Debug New lap")
