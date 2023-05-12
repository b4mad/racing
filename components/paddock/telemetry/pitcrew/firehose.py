from telemetry.pitcrew.logging import LoggingMixin
from .session import Session
import django.utils.timezone


class Firehose(LoggingMixin):
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

            session = Session(topic, start=now)
            session.driver = driver
            session.session_id = session_id
            self.log_debug(f"New session: {topic}")
            session.game_name = game
            session.track = track
            session.car = car
            session.session_type = session_type
            self.sessions[topic] = session

        session = self.sessions[topic]
        session.signal(payload, now)

    # TODO: clear sessions every now and then
    def clear_sessions(self, now):
        delete_sessions = []
        for topic, session in self.sessions.items():
            # delete session without updates for 10 minutes
            if (now - session["end"]).seconds > 600:
                delete_sessions.append(topic)

            # get the length of the session['laps'] list and count down the index
            # and delete the lap if it has the delete flag set
            for i in range(len(session["laps"]) - 1, -1, -1):
                lap = session["laps"][i]
                if lap.get("delete", False):
                    self.log_debug(f"{topic}\n\t deleting lap {lap['number']}")
                    del session["laps"][i]

        # delete all sessions by iterating over delete_sessions
        for topic in delete_sessions:
            del self.sessions[topic]
            self.log_debug(f"{topic}\n\t deleting inactive session")
