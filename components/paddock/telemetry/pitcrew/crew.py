import os
import threading
import logging
import time
import signal

from .firehose import Firehose
from .mqtt import Mqtt
from .coach_watcher import CoachWatcher
from .session_saver import SessionSaver

from flask_healthz import HealthError


class Crew:
    def __init__(self, debug=False, replay=False):
        self._ready = False
        self._live = False
        self.debug = debug
        self.replay = replay

        topic = "crewchief/#"

        self.firehose = Firehose(debug=debug)
        self.mqtt = Mqtt(self.firehose, topic, replay=replay)

        self.coach_watcher = CoachWatcher(self.firehose, replay=replay)
        self.coach_watcher.sleep_time = 3

        self.session_saver = SessionSaver(self.firehose)
        self.session_saver.sleep_time = 5

        self._stop_event = threading.Event()
        logging.debug("Crew initialized")

    def stop(self):
        self._live = False
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def _handle_sigterm(self, signum, frame):
        logging.info("Received SIGTERM, shutting down...")
        self.stop()

    def live(self):
        if not self._live:
            raise HealthError("not alive")

    def ready(self):
        if not self._ready:
            raise HealthError("not ready yet")

    def run(self):
        # log my process id
        logging.info(f"starting Crew with pid {os.getpid()}")

        # add signal handling for SIGTERM
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        threads = []

        t = threading.Thread(target=self.mqtt.run)
        t.name = "mqtt"
        threads.append(t)

        t = threading.Thread(target=self.coach_watcher.run)
        t.name = "coach_watcher"
        threads.append(t)

        t = threading.Thread(target=self.session_saver.run)
        t.name = "session_saver"
        threads.append(t)

        for t in threads:
            logging.debug(f"starting Thread {t}")
            t.start()

        logging.debug("waiting for threads to be ready...")
        while True:
            if self.mqtt.ready and self.coach_watcher.ready and self.session_saver.ready:
                break
            time.sleep(1)

        logging.debug("..threads are ready")
        self._ready = True
        self._live = True

        while True and not self.stopped():
            time.sleep(1)
            for t in threads:
                if not t.is_alive():
                    self.stop()
                    logging.error(f"Thread {t} died")
                    break

        self.mqtt.stop()
        self.coach_watcher.stop()
        self.session_saver.stop()

        for t in threads:
            logging.debug(f"joining Thread {t}")
            t.join(timeout=60)

        logging.debug("all threads joined... bye")
