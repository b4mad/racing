#!/usr/bin/env python3

import threading
import logging
from coach import Coach
from history import History
from mqtt import Mqtt

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    history = History()
    coach = Coach(history)
    mqtt = Mqtt(coach)

    def history_thread():
        logging.info("History thread starting")
        history.run()

    h = threading.Thread(target=history_thread)
    h.start()
    mqtt.run()
