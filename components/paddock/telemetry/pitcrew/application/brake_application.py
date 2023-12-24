from .application import Application


class BrakeApplication(Application):
    def init(self):
        self.init_messages()
        self.send_response("Starting debug app")

    def init_messages(self):
        self.messages = {}
        for turn, segment in self.segments_by_turn.items():
            if segment.type_brake():
                at = segment.brake_point()
                self.messages[at] = "brake"
            if segment.type_throttle():
                at = segment.throttle_point()
                self.messages[at] = "lift"

    def tick(self):
        msg = self.messages.get(self.distance)
        if msg:
            self.send_response(msg, at=self.distance)
