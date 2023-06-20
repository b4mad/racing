import json

import django.utils.timezone

from telemetry.models import Coach as DbCoach
from telemetry.pitcrew.logging import LoggingMixin

from .history import History
from .message import (
    MessageApex,
    MessageBrake,
    MessageBrakeForce,
    MessageGear,
    MessageThrottle,
    MessageThrottleForce,
    MessageTrailBrake,
)


class Coach(LoggingMixin):
    def __init__(self, history: History, db_coach: DbCoach, debug=False):
        self.history = history
        self.db_coach = db_coach
        self.messages = []
        self.previous_distance = 10_000_000
        self.response_topic = f"/coach/{db_coach.driver.name}"
        self.responses = {}
        self.topic = ""
        self.session_id = "NO_SESSION"
        self.track_walk = False
        self.distance = 0
        self._new_session_starting = False
        self._next_messages = []
        self._error = None

    def filter_from_topic(self, topic):
        frags = topic.split("/")
        driver = frags[1]
        session = frags[2]  # noqa
        game = frags[3]
        track = frags[4]
        car = frags[5]
        filter = {
            "Driver": driver,
            "GameName": game,
            "TrackCode": track,
            "CarModel": car,
            "SessionId": session,
        }
        return filter

    def new_session(self, topic):
        self._new_session_starting = True
        self.topic = topic
        self.log_debug("new session %s", topic)
        filter = self.filter_from_topic(topic)
        self.history.set_filter(filter)
        self.session_id = filter.get("SessionId", "NO_SESSION")
        self.messages = []
        self._next_messages = []
        self.responses = {}
        self.db_coach.refresh_from_db()
        self.track_walk = self.db_coach.track_walk

    def ready(self):
        if self._new_session_starting:
            if not self.history.is_ready():
                if self.history.is_initializing():
                    return False
                error = self.history.get_and_reset_error()
                if error:
                    self.db_coach.error = error
                    self.db_coach.save()
                    self._error = error
                return False

            self.init_messages()

            startup_message = "start coaching "
            try:
                lap_time = self.history.fast_lap.laps.first().time_human()
                startup_message += f"for a lap time of {lap_time}"
            except Exception:
                pass

            if self.track_walk:
                startup_message += " doing a track walk"

            self.say_next(startup_message)
            self.db_coach.status = startup_message
            self.db_coach.fast_lap = self.history.fast_lap
            self.db_coach.error = ""
            self.db_coach.save()

            self.track_length = self.history.track_length

            self._new_session_starting = False

        return True

    def get_and_reset_error(self):
        if self._error:
            error = self._error
            self._error = None
            return error

    def say_next(self, msg):
        self._next_messages.append(msg)

    def notify(self, topic, telemetry, now=None):
        now = now or django.utils.timezone.now()
        if self.topic != topic:
            self.new_session(topic)

        if not self.ready():
            error = self.get_and_reset_error()
            if error:
                return (self.response_topic, error)
            return None

        if self._next_messages:
            messages = self._next_messages
            self._next_messages = []
            return (self.response_topic, messages)

        self.distance = int(telemetry["DistanceRoundTrack"])
        if self.distance == self.previous_distance:
            return None

        if self.distance % 100 == 0:
            self.log_debug(f"distance: {self.distance}")

        distance_diff = self.previous_distance - self.distance
        if self.track_length - 10 > distance_diff >= 1:
            # we jumped at least 1 meters back
            # unless we crossed the start finish line
            # we might have gone off the track or reset the car to the pits
            # hence we reset the messages
            self.log_debug(f"distance: _diff: {distance_diff} -> reset responses")
            self.responses = {}
            self.previous_distance = self.distance
            return

        # self.log_debug(f"distance: {self.distance}: {telemetry['DistanceRoundTrack']}: {telemetry['SpeedMs']}")
        # if distance_diff < -1:
        #     self.log_debug(f"distance: _diff: {distance_diff}")

        work_to_do = self.history.update(now, telemetry)
        if work_to_do and not self.history.threaded:
            self.history.do_work()

        start = self.previous_distance + 1
        stop = self.distance + 1
        if start > stop:
            stop += self.track_length
            self.log_debug(f"distance: wrap around: {start} -> {stop}")

        responses = []
        for distance in range(start, stop):
            responses.extend(self.collect_responses(distance, telemetry))

        self.previous_distance = self.distance
        if responses:
            responses = [json.dumps(resp) for resp in responses]
            return (self.response_topic, responses)

    def collect_responses(self, distance, telemetry):
        return_responses = []

        # FIXME: +100 should be speed dependent
        #
        future_distance = (distance + 20) % self.track_length
        responses = self.get_responses(telemetry, future_distance)
        for response in responses:
            distance = response["distance"]
            r_at = self.responses.get(distance)
            if not r_at:
                r_at = []
                self.responses[distance] = r_at
            r_at.append(response)

        # FIXME
        #  messages are queued for up to 10 seconds in CrewChief
        #  so we send the message less than 10 seconds before its due
        #  if we send messages too late, the driver will have passed the distance
        #  find the distance where
        future_distance = (distance + 10) % self.track_length
        responses = self.responses.pop(future_distance, None)
        if responses:
            if len(responses) > 1:
                responses = self.merge_responses(responses)
            return_responses.extend(responses)
            self.log_debug(f"{self.distance}: {responses}")

        return return_responses

    def get_responses(self, telemetry, future_distance):
        responses = []
        for message in self.messages:
            if self.track_walk:
                response = message.response_track_walk(future_distance, telemetry)
            else:
                response = message.response_hot_lap(future_distance, telemetry)

            if response:
                if not isinstance(response, list):
                    response = [response]
                for resp in response:
                    self.log_debug(f"{self.distance}: get_resp {resp}")
                    responses.append(resp)

        return responses

    def merge_responses(self, responses):
        map = {}
        for response in responses:
            distance = response["distance"]
            if distance not in map:
                map[distance] = []
            map[distance].append(response)

        new_responses = []
        for distance, response_arr in map.items():
            # get highest priority of all responses in response_arr
            priority = max([resp["priority"] for resp in response_arr])
            # filter out all responses with lower priority
            response_arr = [resp for resp in response_arr if resp["priority"] == priority]
            # merge all message strings into one
            # response = response_arr[0]
            # FIXME: if we merge, we should re-calculate the 'at', since we might have
            #        calculated it for a distance based on the length of the message
            #        lets just take the first one for now
            # message = " ".join([resp["message"] for resp in response_arr])
            # response["message"] = message
            response = response_arr[0]
            new_responses.append(response)

        return new_responses

    def init_messages(self):
        self.messages = []
        message_classes = [
            MessageBrake,
            MessageBrakeForce,
            MessageGear,
            MessageThrottle,
            MessageThrottleForce,
            MessageTrailBrake,
            MessageApex,
        ]
        for segment in self.history.segments:
            for message_class in message_classes:
                message = message_class(segment, logger=self.log_debug)
                if message.active:
                    self.messages.append(message)
