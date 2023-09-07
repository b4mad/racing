import json

import django.utils.timezone

from telemetry.models import Coach, SessionType
from telemetry.pitcrew.logging import LoggingMixin

from .application.response import ResponseInstant
from .application.session import Session
from .application.track_guide_application import TrackGuideApplication
from .history import History


class CoachApp(LoggingMixin):
    def __init__(self, history: History, coach_model: Coach, debug=False):
        self.history = history
        self.coach_model = coach_model
        self.response_topic = f"/coach/{coach_model.driver.name}"
        self.init_variables()

    def init_variables(self):
        self.responses = []
        self.topic = ""
        self.session_id = ""
        self.distance = 0
        self.previous_distance = -1

    def filter_from_topic(self, topic):
        frags = topic.split("/")
        driver = frags[1]
        session = frags[2]  # noqa
        game = frags[3]
        track = frags[4]
        car = frags[5]
        session_type = frags[6]
        filter = {
            "Driver": driver,
            "GameName": game,
            "TrackCode": track,
            "CarModel": car,
            "SessionId": session,
            "SessionType": session_type,
        }
        return filter

    def new_session(self, topic):
        self._new_session_starting = True
        self.init_variables()
        self.topic = topic
        filter = self.filter_from_topic(topic)
        self.session_id = filter["SessionId"]
        self.session_type = SessionType.objects.get(type=filter["SessionType"])
        self.log_debug("new session %s", topic)
        self.history.set_filter(filter, self.coach_model.mode)

    def track_length(self):
        return self.history.track_length

    def ready(self):
        if self._new_session_starting:
            if not self.history.is_ready():
                if self.history.is_initializing():
                    return False

                error = self.history.get_and_reset_error()

                if error:
                    self.respond(ResponseInstant(error))
                    self.coach_model.error = error
                    self.coach_model.save()

                return False
            # History is ready
            self.init_app()
            self._new_session_starting = False
        return True

    def init_app(self):
        self.session = Session()
        self.session.track = self.history.track
        self.session.car = self.history.car
        self.session.game = self.history.game
        self.session.session_type = self.session_type
        self.track_guide_app = TrackGuideApplication(self.session)

    def respond(self, response):
        self.responses.append(response)

    def get_and_reset_error(self):
        if self._error:
            error = self._error
            self._error = None
            return error

    def return_messages(self):
        if self.responses:
            responses = [json.dumps(resp.response()) for resp in self.responses]
            self.responses = []
            return (self.response_topic, responses)

    def notify(self, topic, telemetry, now=None):
        now = now or django.utils.timezone.now()
        if self.topic != topic:
            self.new_session(topic)

        if not self.ready():
            return self.return_messages()

        self.distance = int(telemetry["DistanceRoundTrack"])
        if self.distance == self.previous_distance:
            return None

        work_to_do = self.history.update(now, telemetry)
        if work_to_do and not self.history.threaded:
            self.history.do_work()

        start = self.previous_distance + 1
        stop = self.distance + 1
        if start > stop:
            stop += self.track_length()
            self.log_debug(f"distance: wrap around: {start} -> {stop}")

        for distance in range(start, stop):
            if distance % 100 == 0:
                self.log_debug(f"distance: {distance} ({self.distance})")
            for response in self.track_guide_app.notify(distance, telemetry):
                self.respond(response)

        self.previous_distance = self.distance

        return self.return_messages()
