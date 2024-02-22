import datetime

from .application import Application


class BrakeApplication(Application):
    def init(self):
        self.init_messages()
        if self.game.name != "Richard Burns Rally":
            # self.send_response("Brake copilot is not available for Richard Burns Rally")
            self.send_response("This is your brake copilot speaking")
            self.ready = True

    def init_messages(self):
        self.messages = {}
        for turn, segment in self.segments_by_turn.items():
            if segment.type_brake():
                at = segment.brake_point()
                self.messages[at] = self.build_response("brake", at=at)

                force = segment.brake_force()
                if force is not None:
                    msg = "%s percent" % (round(int(force * 100) / 10) * 10)  # 0.73 -> 70
                    response = self.build_response(msg, finish_at=at)
                    self.messages[response.at] = response

            if segment.type_throttle():
                at = segment.throttle_point()
                self.messages[at] = self.build_response("lift", at=at)

                force = segment.throttle_force()
                if force is not None:
                    msg = "lift %s" % (round(int(force * 100) / 10) * 10)
                    response = self.build_response(msg, finish_at=at)
                    self.messages[response.at] = response

    def tick(self):
        msg = self.messages.get(self.distance)
        if msg:
            self.send_response(msg)

    def on_reset_to_pits(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You reset to pits")

    def on_new_lap(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("new lap")

    def on_crash(self, distance: int, telemetry: dict, now: datetime.datetime):
        self.send_response("You crashed")
