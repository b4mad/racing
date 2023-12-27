from .session import Session


class SessionRbr(Session):
    def __init__(self, session_id, start=None):
        super().__init__(session_id, start=start)

    def analyze(self, telemetry, now):
        try:
            distance = telemetry["DistanceRoundTrack"]
            current_lap = telemetry["CurrentLap"]
            lap_time = telemetry["CurrentLapTime"]
        except (KeyError, TypeError):
            if self.telemetry_valid:
                self.log_debug(f"Invalid telemetry: {telemetry}")
                self.telemetry_valid = False
            return

        if distance is None or current_lap is None or lap_time is None:
            if self.telemetry_valid:
                self.log_debug(f"fields are None: {telemetry}")
                self.telemetry_valid = False
            return

        self.telemetry_valid = True

        if not self.current_lap:
            # RBR has only one lap
            self.new_lap(now, 1)
            self.previous_tick_time = -1
            self.previous_tick_distance = 100_000_000
            self.counter_time_not_updated = 0
            self.counter_distance_updated = 0
            self.current_lap.valid = True

        if self.current_lap:
            if distance > self.current_lap.length:
                self.current_lap.length = distance
            self.current_lap.time = lap_time

        # at the end of the session, lap_time stops, but distance keeps increasing
        if self.previous_tick_time == lap_time:
            self.counter_time_not_updated += 1
        else:
            self.counter_time_not_updated = 0

        if self.previous_tick_distance < distance:
            self.counter_distance_updated += 1
        else:
            self.counter_distance_updated = 0

        if self.counter_time_not_updated > 10 and self.counter_distance_updated > 10:
            self.current_lap.finished = True

        self.previous_tick_time = lap_time
        self.previous_tick_distance = distance
