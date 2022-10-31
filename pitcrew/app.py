#!/usr/bin/env python3

import os
import threading
import logging
import time

import daiquiri

from coach import Coach
from history import History
from mqtt import Mqtt

from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc


daiquiri.setup(level=logging.INFO)
_LOGGER = logging.getLogger("pitcrew")


class Crew:
    def __init__(self):
        self.power = True

        self.driver = os.environ.get("CREWCHIEF_USERNAME")
        base_path = f"/{self.driver}/"
        self.app = Dash(
            __name__,
            external_stylesheets=[dbc.themes.VAPOR],
            url_base_pathname=base_path,
        )

        self.app.layout = self.serve_layout

        # https://stackoverflow.com/questions/54729529/python-decorator-as-callback-in-dash-using-dash-object-that-is-an-instance-varia
        self.app.callback(
            Output("power-state", "children"), [Input("power-switch", "value")]
        )(self.show_power_state)

    def serve_layout(self):
        markdown_text = f"""
        # #B4mad Racing Pit Crew

        Driver: {self.driver}
        """

        return dbc.Container(
            [
                dcc.Markdown(children=markdown_text),
                self.power_switch(),
                html.Div(id="power-state"),
            ]
        )

    def power_switch(self):
        switch = html.Div(
            [
                dbc.Switch(
                    id="power-switch",
                    label="Power",
                    value=self.power,
                ),
            ]
        )
        return switch

    def show_power_state(self, power):
        self.power = power
        if power:
            logging.debug("power on")
            return "Power is on"
        else:
            logging.debug("power off")
            return "Power is off"

    def coach_thread(self):
        while True:
            time.sleep(1)
            if self.power:
                self.history = History()
                self.coach = Coach(self.history)
                self.mqtt = Mqtt(self.coach)

                def history_thread():
                    logging.info("History thread starting")
                    self.history.run()

                h = threading.Thread(target=history_thread)

                def mqtt_thread():
                    logging.info("MQTT thread starting")
                    self.mqtt.run()

                c = threading.Thread(target=mqtt_thread)

                threads = list()
                h = threading.Thread(target=history_thread)
                threads.append(h)
                h.start()
                threads.append(c)
                c.start()

                while self.power:
                    time.sleep(1)

                self.mqtt.disconnect()
                self.history.stop()

                for index, thread in enumerate(threads):
                    logging.debug("Main    : before joining thread %d.", index)
                    thread.join()
                    logging.debug("Main    : thread %d done", index)

    def run(self):
        threading.Thread(target=self.coach_thread).start()

        # https://stackoverflow.com/a/68851873
        self.app.run_server(debug=False, port=8050, host="0.0.0.0")


if __name__ == "__main__":
    if os.getenv("DEBUG", "1") == "1":
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug mode enabled")

    if not os.environ.get("CREWCHIEF_USERNAME"):
        os.environ["CREWCHIEF_USERNAME"] = "durandom"
        _LOGGER.warn("CREWCHIEF_USERNAME not set, using default: durandom")

    logging.debug("Starting up the pit crew...")
    crew = Crew()
    crew.run()
