from telemetry.models import TrackGuide

from .application import Application


class TrackGuideApplication(Application):
    def init(self):
        self.recon_laps = True

        # get all notes for track and car
        self.track_guide: TrackGuide | None = TrackGuide.objects.filter(
            car=self.session.car, track=self.session.track
        ).first()
        if not self.track_guide:
            self.send_response("TrackGuide: no track guide found")
        else:
            self.send_response("Let's start the track guide.")
            self.init_notes()

    def init_notes(self):
        for note in self.track_guide.notes.all():
            if note.segment:
                self.get_segment(turn=note.segment)

        # build a dict of DistanceRoundTrack -> [ notes ]
        pass

    def tick(self):
        self.calculate_avg_speed()
        if self.changed_coaching_style():
            if self.is_recon_laps():
                self.send_response("You are driving recon laps")
            else:
                self.send_response("You are driving race pace")

        if self.is_recon_laps():
            self.respond_recon()

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

    def respond_recon(self):
        distance = self.distance_add(20)
        if self.message_playing_at(distance):
            return
        # get all available notes for the current segment
        # get the note for the current distance + some meters ahead
        #
        #
        pass

    def on_reset_to_pits(self):
        self.send_response("TrackGuide: on_reset_to_pits")

    def on_new_lap(self):
        self.send_response("TrackGuide: on_new_lap")
