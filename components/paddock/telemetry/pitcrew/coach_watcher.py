import threading
import logging
import time
from telemetry.models import Driver, Coach

from .coach import Coach as PitCrewCoach
from .history import History
from .mqtt import Mqtt


class CoachWatcher:
    def __init__(self, firehose):
        self.firehose = firehose
        self.sleep_time = 3
        self.active_coaches = {}

        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def drivers(self):
        drivers = set()
        for session in self.firehose.sessions.values():
            # check if session.driver is a Driver object
            if isinstance(session.driver, Driver):
                drivers.add(session.driver)
        return drivers

    def watch_coaches(self):
        while True and not self.stopped():
            # sleep longer than save_sessions, to make sure all DB objects are initialized
            time.sleep(self.sleep_time)
            # logging.info("checking coaches")
            coaches = Coach.objects.filter(driver__in=self.drivers())
            for coach in coaches:
                # logging.info(f"checking coach for {coach.driver}")
                if coach.enabled:
                    if coach.driver.name not in self.active_coaches.keys():
                        logging.debug(f"activating coach for {coach.driver}")
                        self.start_coach(coach.driver.name, coach)
                else:
                    if coach.driver.name in self.active_coaches.keys():
                        logging.debug(f"deactivating coach for {coach.driver}")
                        self.stop_coach(coach.driver)

    def stop_coach(self, driver):
        if driver not in self.active_coaches.keys():
            return
        self.active_coaches[driver][0].disconnect()
        self.active_coaches[driver][1].disconnect()
        del self.active_coaches[driver]

    def start_coach(self, driver, coach, debug=False, replay=False):
        history = History()
        coach = PitCrewCoach(history, coach, debug=debug)
        mqtt = Mqtt(coach, driver, replay=replay)

        def history_thread():
            logging.info(f"History thread starting for {driver}")
            history.run()
            logging.info(f"History thread stopped for {driver}")

        h = threading.Thread(target=history_thread)

        def mqtt_thread():
            logging.info(f"MQTT thread starting for {driver}")
            mqtt.run()
            logging.info(f"MQTT thread stopped for {driver}")

        c = threading.Thread(target=mqtt_thread)

        threads = list()
        threads.append(h)
        threads.append(c)
        c.start()
        h.start()
        self.active_coaches[driver] = [history, mqtt]

    def run(self):
        try:
            self.watch_coaches()
        except Exception as e:
            logging.exception(f"Exception in CoachWatcher: {e}")
            raise e
        finally:
            # stop all coaches
            coaches = list(self.active_coaches.keys())
            for driver in coaches:
                self.stop_coach(driver)

            logging.info("CoachWatcher stopped")
