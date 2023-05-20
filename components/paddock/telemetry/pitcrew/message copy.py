from telemetry.pitcrew.logging import LoggingMixin
from .history import History, Segment
from typing import Any
import json


class Message(LoggingMixin):
    def __init__(self, at, history: History, **kwargs):
        self.history = history
        self.session_id = self.history.session_id
        self.track_length = self.history.track.length
        self.at = at

        self._finished_reading_chain_at = None

        self.msg = kwargs.get("msg", "")
        self.segment = kwargs.get("segment", Segment(self.history))
        self.enabled = kwargs.get("enabled", True)
        self.json_respone = kwargs.get("json_respone", True)
        self.silent = kwargs.get("silent", False)
        self.args = kwargs.get("args", [])
        self.kwargs = kwargs.get("kwargs", {})

        self.next = None
        self.previous = None

        self.related_next = None
        self.related_previous = None

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "at" and self.track_length:
            __value = __value % self.track_length
            self._finished_reading_chain_at = None
            self._send_at = None
        if __name == "msg":
            self._finished_reading_chain_at = None
            self._send_at = None
        super().__setattr__(__name, __value)

    def response(self):
        text_to_read = self.msg
        if self.callable():
            kwargs = self.kwargs.copy()
            # kwargs["message"] = self
            text_to_read = self.msg(self, *self.args, **kwargs)

        if not self.silent and self.json_respone and text_to_read:
            return json.dumps(
                {
                    "distance": self.at,
                    "message": text_to_read,
                    "priority": 9,
                }
            )

        if not self.silent and text_to_read:
            return text_to_read

    def send_at(self):
        if not self._send_at:
            self._send_at = (self.at - 100) % self.track_length
        return self._send_at

    def callable(self):
        return callable(self.msg)

    def read_after(self, message):
        self.related_previous = message
        message.related_next = self

    def silence(self):
        if not self.silent and not self.callable():
            self.log_debug(f"silencing '{self.msg}'")
            self.silent = True
            if self.related_next:
                self.related_next.silence()

    def louden(self):
        if self.silent:
            self.log_debug(f"loudening '{self.msg}'")
            self.silent = False
            if self.related_next:
                self.related_next.louden()

            if self.primary():
                next_msg = self.next
                while next_msg != self:
                    if next_msg.msg == "throttle to 80":
                        True
                    if next_msg.primary():
                        if self.in_read_range(next_msg):
                            next_msg.silence()
                    next_msg = next_msg.next

    def primary(self):
        return not self.callable() and not self.related_previous

    def in_range(self, meters, start, finish):
        if start < finish:
            if meters >= start and meters < finish:
                return True
        else:
            if meters >= start or meters < finish:
                return True

    def in_read_range(self, message):
        start = message.at
        finish = message.finished_reading_chain_at()
        self_start = self.at
        self_finish = self.finished_reading_chain_at()

        if self.in_range(start, self_start, self_finish):
            return True
        if self.in_range(finish, self_start, self_finish):
            return True
        return False

    def read_time(self):
        if not self.msg:
            raise Exception("no message - can't calculate read time")
        words = len(self.msg.split(" "))
        return words * 0.8  # avg ms per word

    def finished_at(self):
        return (self.at + self.read_time()) % self.track_length

    def finish_at(self, at=None):
        if not at:
            at = self.at
        read_time = self.read_time()
        respond_at = self.history.offset_distance(at, seconds=read_time)
        self.at = respond_at

    def finished_reading_chain_at(self):
        if not self.related_next:
            if not self._finished_reading_chain_at:
                self._finished_reading_chain_at = (self.at + self.read_time()) % self.track_length
            return self._finished_reading_chain_at

        self._finished_reading_chain_at = self.related_next.finished_reading_chain_at()
        return self._finished_reading_chain_at
