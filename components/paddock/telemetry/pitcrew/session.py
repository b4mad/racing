import django.utils.timezone
import logging
from telemetry.models import Game


class Lap:
    def __init__(self, number, time=-1.0, valid=False, length=-1, start=None, end=None):
        self.number = number
        self.start = start
        self.end = end
        self.length = length
        self.time = time
        self.finished = False
        self.valid = valid
        self.persisted = False

    def __str__(self):
        return f"Lap {self.number}: {self.time} / valid {self.valid}"

    def __repr__(self):
        return self.__str__()


class Session:
    def __init__(self, id):
        self.id = id
        self.start = django.utils.timezone.now()
        self.end = self.start
        self.laps = {}
        self.driver = ""
        self.session_id = ""
        self.game = Game()
        self.game_name = ""
        self.track = ""
        self.car = ""
        self.session_type = ""
        self.record = None

        self.current_lap_time = -1
        self.distance_round_track = 1_000_000_000
        self.current_lap = None
        self.previous_lap = None
        self.previous_distance = -1
        self.previous_lap_time = -1
        self.previous_lap_time_previous = -1
        self.telemetry_valid = True

    def log(self, message, level=logging.DEBUG):
        if level == logging.DEBUG:
            logging.debug(f"{self.session_id}: {message}")
        elif level == logging.INFO:
            logging.info(f"{self.session_id}: {message}")

    def log_debug(self, message):
        self.log(message, level=logging.DEBUG)

    def log_info(self, message):
        self.log(message, level=logging.INFO)

    def signal(self, telemetry, now=None):
        now = now or django.utils.timezone.now()
        self.end = now
        self.analyze(telemetry, now)

    def log_laps(self):
        for lap in self.laps:
            logging.debug(
                f"{self.driver} lap {lap['number']:02d}: {lap['time']}"
                + f" - valid: {lap['valid']} - finished: {lap['finished']}"
            )

    def new_lap(self, now, lap_number):
        lap = Lap(lap_number, start=now, end=now)
        self.laps.get(lap_number, lap)
        self.laps[lap_number] = lap
        self.previous_lap = self.current_lap
        if self.previous_lap:
            self.previous_lap.end = now
        self.current_lap = lap
        return lap

    def analyze(self, telemetry, now):
        distance = telemetry.get("DistanceRoundTrack", None)
        current_lap = telemetry.get("CurrentLap", None)
        lap_time_previous = telemetry.get("LapTimePrevious", None)
        lap_is_valid = telemetry.get("CurrentLapIsValid", None)
        previous_lap_was_valid = telemetry.get("PreviousLapWasValid", None)
        lap_time = telemetry.get("CurrentLapTime", None)

        if (
            distance is None
            or current_lap is None
            or lap_time_previous is None
            or lap_is_valid is None
            or lap_time is None
            or previous_lap_was_valid is None
        ):
            if self.telemetry_valid:
                self.log_debug(f"Invalid telemetry: {telemetry}")
            self.telemetry_valid = False
            return

        self.telemetry_valid = True
        # check if we're in a new lap, i.e. we're driving over the finish line
        #   ie. distance is lower than the previous distance
        #   and below a threshold of 10 meters
        if distance < self.previous_distance and distance < 10:
            self.new_lap(now, current_lap)
            self.log_debug(f"{self.driver} new lap: {current_lap}")

        if self.current_lap:
            self.current_lap.length = distance
            self.current_lap.valid = lap_is_valid
            # self.current_lap.time = lap_time

        if lap_time_previous != self.previous_lap_time_previous:
            if self.previous_lap:
                self.previous_lap.time = lap_time_previous
                self.previous_lap.valid = previous_lap_was_valid
                self.previous_lap.finished = True
                self.log_debug(
                    f"lap {self.previous_lap.number} time {lap_time_previous} valid {previous_lap_was_valid}"
                )

        self.previous_distance = distance
        self.previous_lap_time = lap_time
        self.previous_lap_time_previous = lap_time_previous
        return

    def analyze_iracing(self, telemetry, now):
        current_lap = int(telemetry.get("CurrentLap", -1))
        # start a new lap if current_lap increases
        if current_lap > self.current_lap:
            lap = self.new_lap(now)
            lap["number"] = current_lap
            self.current_lap = current_lap
            logging.debug(f"{self.driver} new lap: {lap['number']}")

        lap = self.laps[-1]
        previous_lap = self.laps[-2] if len(self.laps) > 1 else None

        lap_time_previous = telemetry.get("LapTimePrevious", -1)
        current_lap_is_valid = telemetry.get("CurrentLapIsValid", False)

        # its an outlap if CurrentLapTime is 0

        lap["end"] = now
        lap["length"] = telemetry.get("DistanceRoundTrack", -1)
        lap["valid"] = current_lap_is_valid

        if lap_time_previous > 0 and previous_lap:
            if lap_time_previous != previous_lap["time"]:
                logging.debug(
                    f"{self.driver} setting previous lap time from"
                    + f"{previous_lap['time']} to {lap_time_previous}"
                )
                previous_lap["time"] = lap_time_previous
                previous_lap["valid"] = telemetry.get("PreviousLapWasValid", False)
                previous_lap["finished"] = True
                self.log_laps()

    def analyze_old(self, telemetry, now):
        length = telemetry.get("DistanceRoundTrack", None)
        speed = telemetry.get("SpeedMs", None)
        lap_time = telemetry.get("CurrentLapTime", None)
        current_lap = telemetry.get("CurrentLap", None)

        if length is None or speed is None or lap_time is None or current_lap is None:
            logging.error("Invalid telemetry: %s", telemetry)
            logging.error(
                f"\tlength: {length}, speed: {speed}, lap_time: {lap_time}, current_lap: {current_lap}"
            )
            return

        threshold = speed * 0.5
        new_lap = False
        previous_length = -1
        if len(self.laps) == 0:
            #  start a new lap if
            #  * DistanceOnTrack starts at 0 # we drive over the finish line
            #    we're sampling a 60hz, with the speed we should see a lap start
            #      (speed * 0.16) meters past the finish line
            if length < threshold:
                new_lap = True
        else:
            lap = self.laps[-1]
            previous_length = lap["length"]
            # start a new lap if cross the finish line
            if length < threshold and length < lap["length"]:
                logging.info(
                    f"{self.session_id}\n\t finishing lap at length {previous_length}"
                    + f" and time {lap['time']}"
                )
                lap["finished"] = True
                new_lap = True

        if new_lap:
            lap = {
                "start": now,
                "end": now,
                "length": length,
                "time": lap_time,
                "finished": False,
                "number": current_lap,
                # if time is less than 5 seconds, lap is active
                "active": lap_time < 5,
                "inactive_log_time": now,
                "valid": False,
            }
            self.laps.append(lap)
            logging.info(
                f"{self.session_id}\n\t new lap length {length} < threshold {threshold}"
                + f" and < previous lap length {previous_length}, active: {lap['active']}, time: {lap_time}"
            )
            return

        if len(self.laps) > 0:
            lap = self.laps[-1]

            if lap["active"]:
                # mark not active if we jump back more than 50 meters
                distance_since_previous_tick = length - lap["length"]
                if distance_since_previous_tick < -50:
                    logging.info(
                        f"{self.session_id}\n\t lap not active, jump {distance_since_previous_tick}m\n"
                        + f"\t\t lap length {lap['length']} jumped to length {length}"
                    )
                    lap["active"] = False
                    return

                # FIXME mark not active if we cut the track

                previous_lap_time = lap["time"]
                if lap_time < previous_lap_time:
                    logging.info(
                        f"{self.session_id}\n\t stop measuring time at {lap_time}s for {previous_lap_time}s / {length}m"
                    )
                    lap["active"] = False
                else:
                    lap["end"] = now
                    lap["length"] = length
                    lap["time"] = lap_time
            elif (lap_time < lap["time"] or lap_time == 0) and lap["start"] == lap[
                "end"
            ]:
                # start measuring time if we're past the threshold and the time started
                #  some games have a delay on CurrentLapTime
                logging.info(
                    f"{self.session_id}\n\t start measuring time at lap.time {lap['time']} / time {lap_time}"
                )
                lap["active"] = True
                lap["end"] = now
                lap["length"] = length
                lap["time"] = lap_time
            else:
                if (now - lap["inactive_log_time"]).seconds > 120:
                    lap["inactive_log_time"] = now
                    logging.info(
                        f"{self.session_id}\n\t lap not active, time {lap_time} > lap.time {lap['time']}"
                    )
