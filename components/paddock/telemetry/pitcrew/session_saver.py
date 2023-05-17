import threading
import logging
import time
from telemetry.models import Game, Driver, SessionType
from django.db import IntegrityError


class SessionSaver:
    def __init__(self, firehose):
        self.firehose = firehose
        self.sleep_time = 10

        self._stop_event = threading.Event()
        self.ready = False

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def save_sessions_loop(self):
        while True and not self.stopped():
            self.save_sessions()
            self.ready = True
            time.sleep(self.sleep_time)

    def save_sessions(self):
        session_ids = list(self.firehose.sessions.keys())
        for session_id in session_ids:
            session = self.firehose.sessions.get(session_id)

            # save session to database
            # TODO: update session details if they change (e.g. end time)
            if not session.record:
                try:
                    session.driver, created = Driver.objects.get_or_create(name=session.driver)
                    session.game, created = Game.objects.get_or_create(name=session.game_name)
                    (
                        session.session_type,
                        created,
                    ) = SessionType.objects.get_or_create(type=session.session_type)
                    session.car, created = session.game.cars.get_or_create(name=session.car)
                    session.track, created = session.game.tracks.get_or_create(name=session.track)
                    (
                        session.record,
                        created,
                    ) = session.driver.sessions.get_or_create(
                        session_id=session.session_id,
                        session_type=session.session_type,
                        game=session.game,
                        defaults={"start": session.start, "end": session.end},
                    )
                    logging.debug(f"{session.session_id}: Saving session {session_id}")
                except Exception as e:
                    # TODO add error to session to expire
                    logging.error(f"{session.session_id}: Error saving session {session_id}: {e}")
                    continue

            lap_numbers = list(session.laps.keys())
            for lap_number in lap_numbers:
                lap = session.laps.get(lap_number)
                if session.record and lap.finished and not lap.persisted:
                    # check if lap length is within 98% of the track length
                    track = session.track

                    # track_length = track.length
                    # if lap.length < track_length * 0.98:
                    #     lstring = (
                    #         f"{lap.number}: {lap.time}s {lap.length}m"
                    #     )
                    #     logging.info(
                    #         f"{session.session_id}: Discard lap {lstring} - track length {track_length}m"
                    #     )
                    #     # FIXME: this is a hack to prevent the lap from being saved again
                    #     lap.persisted = True
                    #     continue

                    try:
                        lap_record = session.record.laps.create(
                            number=lap.number,
                            car=session.car,
                            track=track,
                            start=lap.start,
                            end=lap.end,
                            length=lap.length,
                            valid=lap.valid,
                            time=lap.time,
                        )
                        logging.info(f"{session.session_id}: Saving lap {lap_record}")
                        session.record.end = session.end
                        session.record.save_dirty_fields()
                        lap.persisted = True
                    except IntegrityError as e:
                        logging.error(f"{session.session_id}: Error saving lap {lap.number}: {e}")
                        lap.persisted = True
                    except Exception as e:
                        logging.error(f"{session.session_id}: Error saving lap {lap.number}: {e}")

                    lap_length = int(lap.length)
                    if lap_length > track.length:
                        track.refresh_from_db()
                        if lap_length > track.length:
                            logging.info(
                                f"{session.session_id}: updating {track.name} "
                                + f"length from {track.length} to {lap_length}"
                            )
                            track.length = lap_length
                            track.save()

    def run(self):
        self.save_sessions_loop()
