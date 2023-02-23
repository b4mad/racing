import django.utils.timezone
import logging
from telemetry.models import Game


class Session:
    def __init__(self, id):
        self.id = id
        self.start = django.utils.timezone.now()
        self.end = self.start
        self.laps = []
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
        self.current_lap = -1

    def signal(self, telemetry):
        now = django.utils.timezone.now()
        self.end = now
        if self.game_name == "iRacing":
            self.analyze_iracing(telemetry, now)
        else:
            self.analyze(telemetry, now)

    def log_laps(self):
        for lap in self.laps:
            logging.debug(
                f"{self.driver} lap {lap['number']:02d}: {lap['time']}"
                + f" - valid: {lap['valid']} - finished: {lap['finished']}"
            )

    def new_lap(self, now):
        lap = {
            "start": now,
            "end": now,
            "number": -1,
            "length": -1,
            "time": -1,
            "finished": False,
            "valid": False,
        }
        self.laps.append(lap)
        return lap

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

    def analyze(self, telemetry, now):
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
