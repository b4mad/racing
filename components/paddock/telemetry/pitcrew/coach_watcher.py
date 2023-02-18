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
            drivers = self.drivers()
            # collect all driver names
            # driver_names = [driver.name for driver in drivers]
            # logging.info("checking coaches for drivers: %s", ", ".join(driver_names))
            coaches = Coach.objects.filter(driver__in=drivers)
            for coach in coaches:
                # logging.info(f"{coach.driver} coach enabled: {coach.enabled}")
                if coach.enabled:
                    if coach.driver.name not in self.active_coaches.keys():
                        logging.debug(f"activating coach for {coach.driver}")
                        self.start_coach(coach.driver.name, coach)
                else:
                    if coach.driver.name in self.active_coaches.keys():
                        logging.debug(f"deactivating coach for {coach.driver}")
                        self.stop_coach(coach.driver.name)

    def stop_coach(self, driver_name):
        if driver_name not in self.active_coaches.keys():
            return
        self.active_coaches[driver_name][0].disconnect()
        self.active_coaches[driver_name][1].disconnect()
        del self.active_coaches[driver_name]

    def start_coach(self, driver_name, coach, debug=False, replay=False):
        history = History()
        coach = PitCrewCoach(history, coach, debug=debug)
        mqtt = Mqtt(coach, driver_name, replay=replay)

        def history_thread():
            logging.info(f"History thread starting for {driver_name}")
            history.run()
            logging.info(f"History thread stopped for {driver_name}")

        h = threading.Thread(target=history_thread)
        h.name = f"history-{driver_name}"

        def mqtt_thread():
            logging.info(f"MQTT thread starting for {driver_name}")
            mqtt.run()
            logging.info(f"MQTT thread stopped for {driver_name}")

        c = threading.Thread(target=mqtt_thread)
        c.name = f"mqtt-{driver_name}"

        threads = list()
        threads.append(h)
        threads.append(c)
        c.start()
        h.start()
        self.active_coaches[driver_name] = [history, mqtt]

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
