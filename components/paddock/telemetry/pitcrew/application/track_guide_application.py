import datetime

from telemetry.models import TrackGuide

from .application import Application


class Note:
    def __init__(self, note, finish_at):
        self.note = note
        self.segments = []
        self.at = None
        self.finish_at = finish_at


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
            self.init_recon_notes()

    def init_notes(self):
        self.distance_notes = {}
        self.segment_notes = {}
        # store notes by segment / landmarks
        for track_note in self.track_guide.notes.all():
            finish_at = False
            note = Note(track_note, finish_at)

            if track_note.segment:
                segment = self.get_segment(turn=track_note.segment)
                note.segments.append(segment)
            else:
                note.segments = self.segments_for_landmark(track_note.landmark)
                segment = note.segments[0]

            if track_note.at:
                snippet = track_note.at
            elif track_note.finish_at:
                snippet = track_note.finish_at
                finish_at = True
            else:
                snippet = "brake_point() or throttle_point()"
                finish_at = True

            note.at = self.eval_at(snippet, segment)

            if not note.at:
                # FIXME bubble up to UI
                self.log_error(f"DISCARDING NOTE: note {track_note} has no at - data {note}")
                continue

            distance = note.at
            if distance not in self.distance_notes:
                self.distance_notes[distance] = []
            self.distance_notes[distance].append(note)

            for segment in note.segments:
                if segment not in self.segment_notes:
                    self.segment_notes[segment] = set()
                self.segment_notes[segment].add(note)

    def init_recon_notes(self, segment=None):
        if segment is None:
            self.recon_segment_notes = {}
            self.recon_distance_notes = {}

        recon_notes = []
        for segment_key, notes in self.segment_notes.items():
            if segment and segment_key != segment:
                continue
            self.recon_segment_notes[segment_key] = notes.copy()
            recon_notes.extend(notes)

        for note in recon_notes:
            distance = note.at
            if distance not in self.recon_distance_notes:
                self.recon_distance_notes[distance] = []
            self.recon_distance_notes[distance].append(note)

    def get_recon_note(self, distance):
        notes = self.recon_distance_notes.get(distance, [])
        note = None
        if notes:
            note = notes.pop(0)
            for segment in note.segments:
                self.recon_segment_notes[segment].discard(note)
                if len(self.recon_distance_notes) == 0:
                    self.log_debug(f"reset recon notes for segment {segment}")
                    self.init_recon_notes(segment=segment)
        return note

    def tick(self):
        if not self.track_guide:
            return
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
        if self.is_recon_laps() and self.avg_speed_pct > 0.9:
            self.recon_laps = False
            return True
        elif not self.is_recon_laps() and self.avg_speed_pct < 0.9:
            self.recon_laps = True
            return True
        return False

    def respond_recon(self):
        distance = self.distance_add(self.distance, 300)
        if self.message_playing_at(distance):
            return
        note = self.get_recon_note(distance)
        if note:
            track_note = note.note
            message = track_note.message
            segment = note.segments[0]
            max_distance_delta = self.max_distance_delta(segment)
            at = note.at
            if note.finish_at:
                response = self.send_response(message, finish_at=at, max_distance_delta=max_distance_delta)
            else:
                response = self.send_response(message, at=at, max_distance_delta=max_distance_delta)

            if -100 < (response.at - self.distance) < 0:
                self.log_error(f"response {response} cant be played")

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You reset to pits - I reset messages")

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass

    def on_crash(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You crashed - drive a bit slower")
