import datetime
from collections import deque

from telemetry.models import TrackGuide

from .application import Application


class Note:
    def __init__(self, note):
        self.note = note
        self.segments = []
        self.at = None
        self.response = None


class Turn:
    def __init__(self, id, app: Application):
        self.id = id
        self.start = 0
        self.end = 0
        self.notes = []
        self.app = app
        self.segment = None
        self.responses = deque()
        self._current_response = None

    def is_in_turn(self, distance):
        return True
        return self.start <= distance <= self.end

    def get_response(self, distance):
        # if distance > self._current_response.at:
        #     return self.set_next_response(distance)
        if self._current_response and self._current_response.at == distance:
            response = self._current_response
            self.set_next_response(distance)
            return response

    def set_next_response(self, distance):
        self.responses.rotate(-1)
        self._current_response = self.responses[0]

    def build_response(self, note):
        finish_at = False
        if note.at:
            snippet = note.at
        elif note.finish_at:
            snippet = note.finish_at
            finish_at = True
        else:
            snippet = "brake_point() or throttle_point()"
            finish_at = True

        at = self.app.eval_at(snippet, self.segment)

        if not at:
            raise Exception(f"DISCARDING NOTE: note {note} has no at - data {note}")

        # build the response
        max_distance_delta = self.app.max_distance_delta(self.segment)
        if finish_at:
            response = self.app.build_response(note.message, finish_at=at, max_distance_delta=max_distance_delta)
        else:
            response = self.app.build_response(note.message, at=at, max_distance_delta=max_distance_delta)
        response.sort_at = at
        return response

    def add_note(self, note):
        if note.mode != "recon":
            return

        if not self.notes:
            self.init_from_note(note)

        response = self.build_response(note)
        response.sort_key = f"{note.sort_key}"
        responses = list(self.responses)
        responses.append(response)
        responses.sort(key=lambda x: (x.sort_key, x.sort_at))
        self.responses = deque(responses)
        self._current_response = self.responses[0]

    def init_from_note(self, note):
        if note.segment:
            self.segment = self.app.get_segment(note.segment)
            self.start = self.segment.start
            self.end = self.segment.end
        elif note.landmark:
            self.segment = self.app.get_segment_at(note.landmark.start)
            self.start = note.landmark.start
            self.end = note.landmark.end
        else:
            raise Exception("No segment or landmark")


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
            self.init_turns()

    def init_turns(self):
        self.turns = {}
        for note in self.track_guide.notes.all():
            turn_id = note.segment or note.landmark.name
            turn = self.turns.get(turn_id, None)
            if not turn:
                turn = Turn(turn_id, self)
                self.turns[turn_id] = turn

            try:
                turn.add_note(note)
            except Exception as e:
                self.log_error(e)

    def init_notes(self):
        self.distance_notes = {}
        self.segment_notes = {}
        # store notes by segment / landmarks
        for track_note in self.track_guide.notes.all():
            note = Note(track_note)
            finish_at = False

            if track_note.segment:
                segment = self.get_segment(turn=track_note.segment)
                note.segments.append(segment)
            else:
                # FIXME: doesnt seem to work
                # we'll also play notes for other segments...
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

            at = self.eval_at(snippet, segment)

            if not at:
                # FIXME bubble up to UI
                self.log_error(f"DISCARDING NOTE: note {track_note} has no at - data {note}")
                continue

            # build the response
            max_distance_delta = self.max_distance_delta(segment)
            if finish_at:
                response = self.build_response(track_note.message, finish_at=at, max_distance_delta=max_distance_delta)
            else:
                response = self.build_response(track_note.message, at=at, max_distance_delta=max_distance_delta)
            note.response = response
            note.at = response.at

            distance = response.at
            if distance not in self.distance_notes:
                self.distance_notes[distance] = []
            self.distance_notes[distance].append(note)

            for segment in note.segments:
                if segment not in self.segment_notes:
                    self.segment_notes[segment] = []
                self.segment_notes[segment].append(note)

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

    def get_recon_note(self, distance, blast=1):
        for blast_distance in range(distance - blast, distance + blast + 1):
            blast_distance = self.distance_add(blast_distance, 0)

            note = self.get_recon_note_at(blast_distance)
            if note:
                return note

    def get_recon_note_at(self, distance):
        notes = self.recon_distance_notes.get(distance, [])
        note = None
        if notes:
            note = notes.pop(0)
            # self.log_error(f"LEN seg: {len(note.segments)}")
            for segment in note.segments:
                # self.log_error(f"LEN: {len(self.recon_segment_notes[segment])}")
                if note in self.recon_segment_notes[segment]:
                    self.recon_segment_notes[segment].remove(note)
                if len(self.recon_segment_notes[segment]) == 0:
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
        else:
            self.respond_pace()

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

    def respond_pace(self):
        pass

    def respond_recon(self):
        add_distance = 100
        distance = self.distance_add(self.distance, add_distance)
        if self.message_playing_at(distance):
            return

        for turn in self.turns.values():
            if turn.is_in_turn(distance):
                response = turn.get_response(distance)
                if response:
                    self.send_response(response)
                    break

    def respond_recon_old(self):
        # FIXME: seconds_lookahead should be constant, but depend on recon or pace
        seconds_lookahead = 3  # 10 is the timeout for a queued message
        add_distance = int(self.telemetry.get("SpeedMs", 50) * seconds_lookahead)
        distance = self.distance_add(self.distance, add_distance)
        # self.log_debug(f"respond_recon: {self.distance} -> {distance} (+{add_distance})")
        if self.message_playing_at(distance):
            return
        # a dynamic lookahead means, we could miss some messages
        # therefore we have a blast radius at self.get_recon_note
        note = self.get_recon_note(distance)
        if note:
            if note.response.message.startswith("Exit wide to the grass - be careful of"):
                pass
            self.send_response(note.response)

            # if -100 < (response.at - self.distance) < 0:
            #     self.log_error(f"response {response} cant be played")

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You reset to pits - I reset messages")

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        pass

    def on_crash(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You crashed - drive a bit slower")
