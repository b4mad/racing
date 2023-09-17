import datetime

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
            self.init_recon_notes()

    def init_notes(self):
        self.distance_notes = {}
        self.segment_notes = {}
        # store notes by segment / landmarks
        for note in self.track_guide.notes.all():
            finish_at = False
            data = {
                "note": note,
                "segments": [],
                "at": None,
                "finish_at": finish_at,
            }

            if note.segment:
                segment = self.get_segment(turn=note.segment)
                data["segments"].append(segment)
            else:
                data["segments"] = self.segments_for_landmark(note.landmark)
                segment = data["segments"][0]

            if note.at:
                snippet = note.at
            elif note.finish_at:
                snippet = note.finish_at
                finish_at = True
            else:
                snippet = "brake_point() or throttle_point()"
                finish_at = True

            data["at"] = self.eval_at(snippet, segment)

            if not data["at"]:
                # FIXME bubble up to UI
                self.log_error(f"DISCARDING NOTE: note {note} has no at - data {data}")
                continue

            distance = data["at"]
            if distance not in self.distance_notes:
                self.distance_notes[distance] = []
            self.distance_notes[distance].append(data)

            for segment in data["segments"]:
                if segment not in self.segment_notes:
                    self.segment_notes[segment] = []
                self.segment_notes[segment].append(data)

    def init_recon_notes(self):
        self.recon_segment_notes = {}
        for segment, notes in self.segment_notes.items():
            self.recon_segment_notes[segment] = notes.copy()

        self.recon_distance_notes = {}
        for distance, notes in self.distance_notes.items():
            self.recon_distance_notes[distance] = notes.copy()

    def get_recon_note(self, distance):
        notes = self.recon_distance_notes.get(distance, [])
        note = None
        if notes:
            note = notes.pop(0)
            if not notes:
                # notes are empty at this distance
                # remove from dict
                del self.recon_distance_notes[distance]
            if len(self.recon_distance_notes) == 0:
                # FIXME: reset notes for segment, once the segment is empty
                self.log_debug("reset recon notes")
                self.init_recon_notes()
            # segment = self.get_segment_at(distance)
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
        note_info = self.get_recon_note(distance)
        if note_info:
            note = note_info["note"]
            segment = note_info["segments"][0]
            max_distance_delta = self.max_distance_delta(segment)
            at = note_info["at"]
            if note_info["finish_at"]:
                response = self.send_response(note.message, finish_at=at, max_distance_delta=max_distance_delta)
            else:
                response = self.send_response(note.message, at=at, max_distance_delta=max_distance_delta)

            if -100 < (response.at - self.distance) < 0:
                self.log_error(f"response {response} cant be played")

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You reset to pits - I reset messages")

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass

    def on_crash(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You crashed - drive a bit slower")
