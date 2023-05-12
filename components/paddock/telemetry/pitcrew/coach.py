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
        messages = sorted(self.messages, key=lambda k: k["at"])

        closest_message = messages[0]
        for i in range(len(messages) - 1, 0, -1):
            msg = messages[i]
            if msg["at"] < meter:
                break
            closest_message = msg
        return closest_message

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

    def set_filter(self, filter):
        self.history.set_filter(filter)
        self.messages = []

    def notify(self, topic, payload, now=None):
        now = now or django.utils.timezone.now()
        if self.topic != topic:
            self.topic = topic
            logging.debug("new session %s", topic)
            self.set_filter(self.filter_from_topic(topic))
            self.startup_message = ""

        if not self.history.ready:
            if self.history.error:
                self.db_coach.error = self.history.error
                self.db_coach.save()
                return (self.response_topic, self.history.error)
            return None

        if self.history.ready and self.history.startup_message:
            self.track_length = self.history.track.length
            if self.startup_message != self.history.startup_message:
                self.startup_message = self.history.startup_message
                self.db_coach.status = self.startup_message
                self.db_coach.save()
                return (self.response_topic, self.startup_message)

        if not self.messages:
            self.init_messages()
            self.link_messages()
            self.prioritize_messages()

        response = self.get_response(payload, now)
        # logging.debug(f"payload: {payload}")
        # logging.debug(f"response: {response}")
        if response:
            return (self.response_topic, response)

    def get_response(self, telemetry, now):
        work_to_do = self.history.update(now, telemetry)
        if work_to_do and not self.history.threaded:
            self.history.do_work()

        distance_round_track = telemetry["DistanceRoundTrack"]
        # logging.debug(f"distance_round_track: {distance_round_track:.1f}")
        if (distance_round_track - self.previous_distance) < -50:
            # we jumped at least 50 meters back
            # unless we crossed the start finish line
            # we might have gone off the track or reset the car to the pits
            # hence we reset the messages
            if abs(self.track_length - distance_round_track - self.previous_distance) > 5:
                self.current_message = self.get_closest_message(distance_round_track)
                logging.debug(f"distance_round_track: {distance_round_track:.1f}")
                logging.debug(f"previous_distance: {self.previous_distance:.1f}")
                logging.debug(f"searching next_message: {self.current_message.at} {self.current_message.msg}")
        self.previous_distance = distance_round_track

        message = self.current_message
        # FIXME: if distance is at the end of the track. -> modulo track_length
        # FIXME: maybe make this dependent on the speed of the car
        distance = abs(message.send_at() - distance_round_track)
        # logging.debug(f"message at: {message['at']} - on_track: {distance_round_track} - distance: {distance:.1f}")

        if distance < 10:
            # self.messages.append(self.messages.pop(0))
            self.current_message = message.next
            logging.debug(f"next_message: {self.current_message.at} {self.current_message.msg}")

            if message.callable():
                logging.debug(f"{distance_round_track:.1f}: {message.msg}")

            text_to_read = message.response()

            if text_to_read:
                logging.debug(f"{distance_round_track:.1f}: {text_to_read}")
            return text_to_read

    def init_messages(self):
        for segment in self.history.segments:
            if segment["mark"] == "brake":
                # gear = ""
                # if segment["gear"]:
                #     gear = f"gear {segment['gear']} "
                # text = gear + "%s percent" % (round(segment["force"] / 10) * 10)
                text = self.brake_message(segment)

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
        log_prefix = f"eval_brake: {message.segment.turn}:"
        new_message = self.brake_message(message.segment)
        old_message = message.related_next.msg
        if new_message:
            if new_message != old_message:
                message.related_next.msg = new_message
                logging.debug(f"{log_prefix} change: {old_message} -> {new_message}")
                message.related_next.louden()
            else:
                logging.debug(f"{log_prefix} keep: {old_message}")
                message.related_next.louden()
        else:
            logging.debug(f"{log_prefix} silencing: {old_message}")
            message.related_next.silence()

    def brake_message(self, segment):
        log_prefix = f"eval_brake: {segment.turn}:"

        gear_fragment = ""
        if segment["gear"]:
            gear_fragment = f"gear {segment['gear']}"
        force_fragment = "%s percent" % (round(segment["force"] / 10) * 10)
        default_message = gear_fragment + " " + force_fragment

        if not segment.has_last_features("brake"):
            logging.debug(f"{log_prefix} no last features: {default_message}")
            return default_message

        new_fragments = []

        # check gear
        last_gear = segment.last_gear_features("gear")
        gear_diff = last_gear - segment["gear"]
        if gear_diff != 0:
            new_fragments.append(gear_fragment)
        logging.debug(f"{log_prefix} gear_diff: {gear_diff}")

        # check brake force
        last_brake_force = segment.last_brake_features("force")
        coach_brake_force = segment.brake_features.get("force")
        force_diff = last_brake_force - coach_brake_force
        force_diff_abs = abs(force_diff)
        logging.debug(f"{log_prefix} force_diff: {force_diff:.2f}")
        if force_diff_abs > 0.3:
            # too much or too little
            new_fragments.append(force_fragment)
        elif force_diff > 0.1:
            new_fragments.append("a bit less")
        elif force_diff < -0.1:
            new_fragments.append("a bit harder")

        # check brake start
        last_brake_start = segment.last_brake_features("start")
        coach_brake_start = segment.brake_features.get("start")
        brake_diff = last_brake_start - coach_brake_start
        brake_diff_abs = abs(brake_diff)
        logging.debug(f"{log_prefix} brake_diff: {brake_diff:.1f}")

        if abs(brake_diff_abs) > 50:
            # too early or too late
            new_fragments = [default_message]
        elif brake_diff > 20:
            # too late
            new_fragments.append("a bit earlier")
        elif brake_diff < -20:
            # too early
            new_fragments.append("a bit later")

        if new_fragments:
            return " ".join(new_fragments)
        else:
            return ""
