from collections import deque

from telemetry.models import TrackGuide

from .application import Application


class TrackGuideApplication(Application):
    def init(self):
        self.speed_pct_history = deque(maxlen=100)
        self.speed_pct_sum = 0.0
        self.avg_speed_pct = 0
        self.recon_laps = True

        # get all notes for track and car
        self.track_guide = TrackGuide.objects.filter(car=self.session.car, track=self.session.track).first()
        if not self.track_guide:
            self.send_response("TrackGuide: no track guide found")
        else:
            self.send_response("Let's start the track guide.")

    def tick(self):
        self.calculate_avg_speed()
        if self.changed_coaching_style():
            if self.is_recon_laps():
                self.send_response("You are driving recon laps")
            else:
                self.send_response("You are driving race pace")

        if self.is_recon_laps():
            self.log_debug(f"recon laps - avg_speed_pct {self.avg_speed_pct}")

    def calculate_avg_speed(self):
        race_pace_speed = self.race_pace_speed_at(self.distance)
        if race_pace_speed:
            speed_pct = self.speed / race_pace_speed
            # Add current speed pct to history
            if len(self.speed_pct_history) == self.speed_pct_history.maxlen:
                # Remove the oldest value from the sum
                self.speed_pct_sum -= self.speed_pct_history[0]
            self.speed_pct_history.append(speed_pct)
            # Add the new value to the sum
            self.speed_pct_sum += speed_pct

            self.avg_speed_pct = self.speed_pct_sum / len(self.speed_pct_history)

    def is_recon_laps(self):
        return self.recon_laps

    def changed_coaching_style(self):
        if self.is_recon_laps() and self.avg_speed_pct > 0.8:
            self.recon_laps = False
            return True
        elif not self.is_recon_laps() and self.avg_speed_pct < 0.8:
            self.recon_laps = True
            return True
        return False

    def on_reset_to_pits(self):
        self.send_response("TrackGuide: on_reset_to_pits")

    def on_new_lap(self):
        self.send_response("TrackGuide: on_new_lap")
