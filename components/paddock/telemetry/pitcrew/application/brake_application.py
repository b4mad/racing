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
                self.messages[at] = self.build_response("brake", at=at)

                # force = segment.brake_force()
                # if force is not None:
                #     msg = "%s percent" % (round(int(force * 100) / 10) * 10)  # 0.73 -> 70
                #     self.
                #     at = self.finish_at(at, msg)

            if segment.type_throttle():
                at = segment.throttle_point()
                self.messages[at] = self.build_response("lift", at=at)

    def tick(self):
        msg = self.messages.get(self.distance)
        if msg:
            self.send_response(msg)
