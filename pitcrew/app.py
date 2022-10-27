#!/usr/bin/env python3

import threading
import logging
from coach import Coach
from history import History
from mqtt import Mqtt

from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

logging.basicConfig(level=logging.DEBUG)

# app = Dash(__name__)
app = Dash(external_stylesheets=[dbc.themes.VAPOR])

markdown_text = """
# B4MAD Racing Pit Crew
"""

app.layout = html.Div(
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


@app.callback(Output("power-state", "children"), Input("power", "value"))
def set_display_children(state):
    return "Power is {}".format(
        state,
    )


def headless():
    history = History()
    coach = Coach(history)
    mqtt = Mqtt(coach)

    def history_thread():
        logging.info("History thread starting")
        history.run()

    h = threading.Thread(target=history_thread)
    h.start()
    mqtt.run()


if __name__ == "__main__":
    h = threading.Thread(target=headless)
    h.start()

    # https://stackoverflow.com/a/68851873
    app.run_server(debug=False)
