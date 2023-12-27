import logging

import django.utils.timezone

from .session import Session
from .session_rbr import SessionRbr


class Firehose:
    def __init__(self, debug=False):
        self.debug = debug
        self.sessions = {}

    def notify(self, topic, payload, now=None):
        now = now or django.utils.timezone.now()
        if topic not in self.sessions:
            try:
                (
                    prefix,
                    driver,
                    session_id,
                    game,
                    track,
                    car,
                    session_type,
                ) = topic.split("/")
            except ValueError:
                # ignore invalid session
                return

            if game == "Richard Burns Rally":
                session = SessionRbr(topic, start=now)
            else:
                session = Session(topic, start=now)

            session.driver = driver
            session.session_id = session_id
            logging.debug(f"New session: {topic}")
            session.game_name = game
            session.track = track
            session.car = car
            session.car_class = payload.get("CarClass", "")
            session.session_type = session_type
            self.sessions[topic] = session

        session = self.sessions[topic]
        session.signal(payload, now)

    # TODO: clear sessions every now and then
    def clear_sessions(self, now):
        """Clear inactive telemetry sessions.

        Loops through all sessions and deletes:
        - Any session inactive for more than 10 minutes
        - Any lap marked for deletion

        Args:
            now (datetime): The current datetime

        """

        delete_sessions = []
        for topic, session in self.sessions.items():
            # Delete session without updates for 10 minutes
            if (now - session["end"]).seconds > 600:
                delete_sessions.append(topic)

            # Delete any lap marked for deletion
            for i in range(len(session["laps"]) - 1, -1, -1):
                lap = session["laps"][i]
                if lap.get("delete", False):
                    logging.debug(f"{topic}\n\t deleting lap {lap['number']}")
                    del session["laps"][i]

        # Delete all inactive sessions
        for topic in delete_sessions:
            del self.sessions[topic]
            logging.debug(f"{topic}\n\t deleting inactive session")
