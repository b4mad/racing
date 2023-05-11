import logging
import django.utils.timezone
from .history import History
from .message import Message
from telemetry.models import Coach as DbCoach

_LOGGER = logging.getLogger(__name__)


class Coach:
    def __init__(self, history: History, db_coach: DbCoach, debug=False):
        self.history = history
        self.previous_history_error = None
        self.db_coach = db_coach
        self.messages = []
        self.previous_distance = 10_000_000
        self.response_topic = f"/coach/{db_coach.driver.name}"
        self.topic = ""

    def new_msg(self, at, **kwargs):
        message = Message(at, self.history)
        for key, value in kwargs.items():
            message[key] = value
        self.messages.append(message)
        return message

    def sort_messages(self, distance):
        # sort messages by distance, keyword argument 'at'
        messages = sorted(self.messages, key=lambda k: k["at"])
        index_of_first_item = 0

        # loop through messages and find index of first item larger than distance
        for i, msg in enumerate(messages):
            index_of_first_item = i
            if msg["at"] > distance:
                break

        return messages[index_of_first_item:] + messages[:index_of_first_item]

    def get_closest_message(self, meter):
        # Find the object with the closest 'at' attribute to 'meter'
        closest = min(self.messages, key=lambda obj: abs(obj.at - meter))
        return closest

    def link_messages(self):
        messages = sorted(self.messages, key=lambda k: k["at"])
        for i in range(len(messages)):
            msg = messages[i]
            msg.silence()
            if i == 0:
                msg.previous = messages[-1]
            else:
                msg.previous = messages[i - 1]
            if i == len(messages) - 1:
                msg.next = messages[0]
            else:
                msg.next = messages[i + 1]

    def prioritize_messages(self):
        for message in self.messages:
            if message.primary():
                message.louden()

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
        }
        return filter

    def notify(self, topic, payload, now=None):
        now = now or django.utils.timezone.now()
        if self.topic != topic:
            self.topic = topic
            logging.debug("new session %s", topic)
            self.set_filter(self.filter_from_topic(topic))

        response = self.get_response(payload, now)
        if response:
            return (self.response_topic, response)

    def set_filter(self, filter):
        self.history.set_filter(filter)
        self.messages = []

    def get_response(self, telemetry, now):
        if not self.history.ready:
            if self.history.error != self.previous_history_error:
                self.previous_history_error = self.history.error
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return self.history.error
            else:
                return None

        work_to_do = self.history.update(now, telemetry)
        if work_to_do and not self.history.threaded:
            self.history.do_work()

        distance_round_track = telemetry["DistanceRoundTrack"]

        if not self.messages:
            self.init_messages()
            self.link_messages()
            self.prioritize_messages()

        if distance_round_track < self.previous_distance:
            self.current_message = self.get_closest_message(distance_round_track)
            self.previous_distance = distance_round_track

        message = self.current_message
        # FIXME: if distance is at the end of the track. -> modulo track_length
        distance = abs(message["at"] - distance_round_track)

        if distance < 10:
            # self.messages.append(self.messages.pop(0))
            self.current_message = message.next

            if message.callable():
                logging.debug(f"{distance_round_track:.1f}: {message.msg}")

            text_to_read = message.response()

            if text_to_read:
                logging.debug(f"{distance_round_track:.1f}: {text_to_read}")
            return text_to_read

    def init_messages(self):
        self.track_length = self.history.track.length
        for segment in self.history.segments:
            if segment["mark"] == "brake":
                gear = ""
                if segment["gear"]:
                    gear = f"gear {segment['gear']} "
                text = gear + "%s percent" % (round(segment["force"] / 10) * 10)

                brake_msg = self.new_msg(segment["start"])
                brake_msg.msg = text
                brake_msg.finish_at()

                features = segment.get("brake_features", {})
                brake_msg_start = self.new_msg(features.get("start"))
                brake_msg_start.msg = "brake"

                msg_eval = self.new_msg(brake_msg.at - 100)
                msg_eval.segment = segment
                msg_eval.msg = self.eval_brake

                brake_msg_start.read_after(brake_msg)
                msg_eval.related_next = brake_msg

            if segment["mark"] == "throttle":
                msg = self.new_msg(segment["start"])
                msg.segment = segment
                to = round(segment["force"] / 10) * 10
                msg.msg = "throttle to %s" % to
                msg.finish_at()

                features = segment.get("throttle_features", {})
                msg_now = self.new_msg(features.get("start"))
                msg_now.segment = segment
                msg_now.msg = "now"

                msg_now.read_after(msg)

    def eval_brake(self, message):
        last_brake_start = message.segment.last_brake_features("start")
        coach_brake_start = message.segment.brake_features.get("start")
        brake_diff = last_brake_start - coach_brake_start
        logging.debug(f"eval_brake: brake_diff: {brake_diff:.1f} for turn {message.segment.turn}")

        if abs(brake_diff) < 10:
            message.related_next.silence()
        else:
            message.related_next.louden()
