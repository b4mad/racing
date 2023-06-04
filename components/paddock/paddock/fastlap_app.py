from dash import html, dcc
from dash.dependencies import Input, Output
from django_plotly_dash import DjangoDash
from telemetry.visualizer import fig_add_features, lap_fig
import base64
import dash
import pickle
import requests


app = DjangoDash("Fastlap", serve_locally=True, add_bootstrap_links=True)

app.layout = html.Div(
    [html.Div(id="graphs-container"), html.Button("Submit", id="submit-val", n_clicks=0, style={"display": "none"})]
)


@app.callback(Output("graphs-container", "children"), [Input("submit-val", "n_clicks")])
def update_graph(n_clicks, session_state=None):
    if n_clicks is None:
        return dash.no_update
    fastlap_url = session_state.get("fastlap_url")
    response = requests.get(fastlap_url)

    if response.status_code != 200:
        return dash.no_update  # If the request failed, don't update the graph

    track_info = pickle.loads(base64.b64decode(response.content))

    graphs = []
    turn = 0
    for segment in track_info:
        turn += 1
        sector = segment["df"]
        throttle_or_brake = segment["mark"]
        brake_features = segment["brake_features"]
        throttle_features = segment["throttle_features"]
        if throttle_or_brake == "brake":
            at = brake_features["start"]
        else:
            at = throttle_features["start"]
        title = f"Turn {turn} - {throttle_or_brake} at {at:.0f}"

        fig = lap_fig(sector)
        if brake_features:
            fig_add_features(fig, brake_features)
        if throttle_features:
            fig_add_features(fig, throttle_features, color="green")

        fig.update_layout(title=dict(text=title))
        graph = dcc.Graph(figure=fig)
        graphs.append(graph)

    return graphs
