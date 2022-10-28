#!/usr/bin/env python3

import os
import threading
import logging
import time
from coach import Coach
from history import History
from mqtt import Mqtt


from dash import Dash, html, dcc, dependencies
import dash_bootstrap_components as dbc

logging.basicConfig(level=logging.DEBUG)


class Crew:
    def __init__(self):
        self.power = True

        base_path = os.environ.get("CREWCHIEF_USERNAME")
        if base_path:
            base_path = "/" + base_path + "/"
        else:
            base_path = "/"
        self.app = Dash(
            __name__,
            external_stylesheets=[dbc.themes.VAPOR],
            url_base_pathname=base_path,
        )

        markdown_text = """
        # B4MAD Racing Pit Crew
        """

        self.app.layout = html.Div(
            [
                dcc.Markdown(children=markdown_text),
                dcc.RadioItems(
                    ["on", "off"],
                    id="power",
                ),
                html.Hr(),
                html.Div(id="power-state"),
            ]
        )

        # https://stackoverflow.com/questions/54729529/python-decorator-as-callback-in-dash-using-dash-object-that-is-an-instance-varia
        self.app.callback(
            dependencies.Output("power-state", "children"),
            dependencies.Input("power", "value"),
        )(self.set_display_children)

    def set_display_children(self, state):
        if state == "off":
            self.mqtt.disconnect()
            self.history.stop()
            self.power = False
            logging.debug("power off")
        else:
            self.power = True
            logging.debug("power on")

        return "Power is {}".format(
            state,
        )

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
                    logging.info("Coach thread starting")
                    self.mqtt.run()

                c = threading.Thread(target=mqtt_thread)

                threads = list()
                h = threading.Thread(target=history_thread)
                threads.append(h)
                h.start()
                threads.append(c)
                c.start()

                for index, thread in enumerate(threads):
                    logging.info("Main    : before joining thread %d.", index)
                    thread.join()
                    logging.info("Main    : thread %d done", index)

    def run(self):
        threading.Thread(target=self.coach_thread).start()

        # https://stackoverflow.com/a/68851873
        self.app.run_server(debug=False, port=8050, host="0.0.0.0")


if __name__ == "__main__":
    logging.debug("Starting up")
    crew = Crew()
    crew.run()
