import threading
import logging
import time
from telemetry.models import Game, Driver, SessionType, Session


class SessionSaver:
    def __init__(self, firehose, debug=False):
        self.firehose = firehose
        self.sleep_time = 10
        self.debug = debug

        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def save_sessions(self):
        while True and not self.stopped():
            time.sleep(self.sleep_time)
            # FIXME: purge old sessions
            session_ids = self.firehose.sessions.keys()
            for session_id in session_ids:
                session = self.firehose.sessions.get(session_id)

                # save session to database
                if not session.record:
                    try:
                        session.driver, created = Driver.objects.get_or_create(
                            name=session.driver
                        )
                        session.game, created = Game.objects.get_or_create(
                            name=session.game_name
                        )
                        (
                            session.session_type,
                            created,
                        ) = SessionType.objects.get_or_create(type=session.session_type)
                        session.car, created = session.game.cars.get_or_create(
                            name=session.car
                        )
                        session.track, created = session.game.tracks.get_or_create(
                            name=session.track
                        )
                        if self.debug:
                            session.record = Session(
                                driver=session.driver,
                                session_id=session.session_id,
                                session_type=session.session_type,
                                game=session.game,
                            )
                        else:
                            (
                                session.record,
                                created,
                            ) = session.driver.sessions.get_or_create(
                                session_id=session.session_id,
                                session_type=session.session_type,
                                game=session.game,
                                defaults={"start": session.start, "end": session.end},
                            )
                    except Exception as e:
                        # TODO add error to session to expire
                        logging.error(f"Error saving session {session_id}: {e}")
                        continue

                if self.debug:
                    continue

                # iterate over laps with index
                for lap in session.laps:
                    if (
                        session.record
                        and lap["finished"]
                        and not lap.get("delete", False)
                    ):
                        # check if lap length is within 98% of the track length
                        track = session.track
                        track_length = track.length
                        lap["delete"] = True  # mark lap for deletion

                        if lap["length"] > track_length * 0.98:
                            try:
                                lap_record = session.record.laps.create(
                                    number=lap["number"],
                                    car=session.car,
                                    track=track,
                                    start=lap["start"],
                                    end=lap["end"],
                                    length=lap["length"],
                                    valid=lap["valid"],
                                    time=lap["time"],
                                )
                                logging.info(
                                    f"Saving lap {lap_record} for session {session_id}"
                                )
                                session.record.end = session.end
                                session.record.save_dirty_fields()
                            except Exception as e:
                                logging.error(f"Error saving lap {lap['number']}: {e}")
                        else:
                            lstring = (
                                f"{lap['number']}: {lap['time']}s {lap['length']}m"
                            )
                            logging.info(
                                f"Discard lap {lstring} for session {session_id} - track length {track_length}m"
                            )

                        lap_length = int(lap["length"])
                        if lap_length > track.length:
                            track.refresh_from_db()
                            if lap_length > track.length:
                                logging.info(
                                    f"updating {track.name} length from {track.length} to {lap_length}"
                                )
                                track.length = lap_length
                                track.save()

    def run(self):
        self.save_sessions()
