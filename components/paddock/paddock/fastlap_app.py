import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

# from django.db.models import Count
from django_plotly_dash import DjangoDash

from telemetry.pitcrew.history import History
from telemetry.pitcrew.message import MessageTrackGuide
from telemetry.racing_stats import RacingStats
from telemetry.visualizer import fig_add_features, lap_fig

app = DjangoDash("Fastlap", serve_locally=True, add_bootstrap_links=True)

app.layout = html.Div(
    [
        dcc.Dropdown(id="game-dropdown", multi=False, placeholder="Select Game"),
        dcc.Dropdown(id="car-dropdown", multi=False, placeholder="Select Car"),
        dcc.Dropdown(id="track-dropdown", multi=False, placeholder="Select Track"),
        html.Div(id="data-table"),
        dbc.Alert("fast lap", id="fast-lap-info", color="info"),
        html.Div(id="graphs-container"),
        html.Button("Submit", id="submit-val", n_clicks=0, style={"display": "none"}),
    ]
)


@app.callback(Output("game-dropdown", "options"), Output("game-dropdown", "value"), [Input("submit-val", "n_clicks")])
def set_games_options(n_clicks, session_state=None):
    racing_stats = RacingStats()
    laps = list(racing_stats.fast_lap_values())
    games = sorted(set(lap["game__name"] for lap in laps))
    game = None
    if session_state is not None:
        game = session_state.get("game__name")
    return [{"label": game, "value": game} for game in games], game


@app.callback(
    Output("car-dropdown", "options"),
    Output("car-dropdown", "value"),
    Output("car-dropdown", "disabled"),
    [Input("game-dropdown", "value")],
)
def set_cars_options(game, session_state=None):
    if game is not None:
        racing_stats = RacingStats()
        laps = list(racing_stats.fast_lap_values())
        cars = sorted(set(lap["car__name"] for lap in laps if lap["game__name"] == game))
        car = None
        if session_state is not None:
            # set game to session_state
            session_state["game__name"] = game
            car = session_state.get("car__name")
        return [{"label": car, "value": car} for car in cars], car, False
    return [], None, True


@app.callback(
    Output("track-dropdown", "options"),
    Output("track-dropdown", "value"),
    Output("track-dropdown", "disabled"),
    [Input("game-dropdown", "value"), Input("car-dropdown", "value")],
)
def set_tracks_options(game, car, session_state=None):
    if game is not None and car is not None:
        racing_stats = RacingStats()
        laps = list(racing_stats.fast_lap_values())
        tracks = sorted(
            set(lap["track__name"] for lap in laps if lap["game__name"] == game and lap["car__name"] == car)
        )
        track = None
        if session_state is not None:
            # set game and car to session_state
            session_state["game__name"] = game
            session_state["car__name"] = car
            track = session_state.get("track__name")
        return [{"label": track, "value": track} for track in tracks], track, False
    return [], None, True


@app.callback(
    Output("data-table", "children"),
    [Input("game-dropdown", "value"), Input("car-dropdown", "value"), Input("track-dropdown", "value")],
)
def update_table(game, car, track, session_state=None):
    # if all([game, car, track]):
    #     return dash.no_update

    if session_state is not None:
        session_state["game__name"] = game
        session_state["car__name"] = car
        session_state["track__name"] = track

    racing_stats = RacingStats()
    # laps = racing_stats.fast_lap_values()
    laps = racing_stats.known_combos(valid=True)
    # laps = laps.annotate(count=Count("id"))
    laps = list(laps)

    data = [
        lap
        for lap in laps
        if (game is None or lap["track__game__name"] == game)
        and (car is None or lap["car__name"] == car)
        and (track is None or lap["track__name"] == track)
    ]

    return dash_table.DataTable(
        columns=[
            {"name": "Game", "id": "track__game__name"},
            {"name": "Car", "id": "car__name"},
            {"name": "Track", "id": "track__name"},
            {"name": "Laps", "id": "count"},
        ],
        data=data,
        style_cell={"textAlign": "left"},
        style_as_list_view=True,
        cell_selectable=False,
        # row_selectable=True,
        style_header={"backgroundColor": "lightgrey", "fontWeight": "bold"},
    )


# https://dash.plotly.com/datatable
# @app.callback(Output('tbl_out', 'children'), Input('tbl', 'active_cell'))
# def update_graphs(active_cell):
#     return str(active_cell) if active_cell else "Click the table"


@app.callback(
    Output("graphs-container", "children"),
    Output("fast-lap-info", "children"),
    [
        Input("submit-val", "n_clicks"),
        Input("game-dropdown", "value"),
        Input("car-dropdown", "value"),
        Input("track-dropdown", "value"),
    ],
)
def update_graph(n_clicks, game, car, track, session_state=None):
    if n_clicks is None or not all([game, car, track]):
        return dash.no_update

    if session_state is not None:
        session_state["game__name"] = game
        session_state["car__name"] = car
        session_state["track__name"] = track

    racing_stats = RacingStats()
    fast_laps = list(racing_stats.fast_laps(game=game, track=track, car=car))
    laps_count = racing_stats.laps(game=game, track=track, car=car, valid=True).count()

    if len(fast_laps) == 0:
        return dash.no_update

    history = History()
    history.set_filter({"GameName": game, "TrackCode": track, "CarModel": car, "Driver": "Jim"})
    history.init()
    # fast_lap = fast_laps[0]
    # segments = fast_lap.data.get("segments", [])
    # for i, segment in enumerate(segments):
    #     next_index = (i + 1) % len(segments)
    #     previous_index = (i - 1) % len(segments)
    #     segment.previous_segment = segments[previous_index]
    #     segment.next_segment = segments[next_index]

    segments = history.segments

    graphs = []
    for segment in segments:
        sector = segment.telemetry
        fig = lap_fig(sector, columns=["Throttle", "Brake"])
        brake_features = segment.brake_features()
        throttle_features = segment.throttle_features()
        if brake_features:
            fig_add_features(fig, brake_features)
        if throttle_features:
            fig_add_features(fig, throttle_features, color="green")

        # fig.update_layout(title=dict(text=title))
        graph = dcc.Graph(figure=fig)
        md = get_segment_header(segment, segment.turn)
        graphs.append(dcc.Markdown(md))
        graphs.append(graph)

        if True:
            # graphs.append(html.Hr())
            # header = html.H6(f"type: {segment.type}")
            # graphs.append(header)
            brake_features = segment.brake_features()
            throttle_features = segment.throttle_features()
            gear_features = segment.gear_features()
            data = [brake_features, throttle_features, gear_features]
            df = pd.DataFrame.from_records(data, index=["brake", "throttle", "gear"])
            table = dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, index=True, size="sm")
            # tb = html.Div(f"tb: {segment.trail_brake()} - {segment._tb_reason}")
            # sector from {segment.start} to {segment.end}
            # graphs.append(tb)
            graphs.append(table)
            graphs.append(html.Hr())

    info = (
        f"Based on a lap time of { history.lap_time_human() } extracted from { history.fast_lap.laps.count() } laps - "
    )
    laps_count = racing_stats.laps(game=game, track=track, car=car, valid=True).count()
    info += f"Valid laps: {laps_count}"

    return graphs, info


def get_segment_header(segment, turn):
    message = MessageTrackGuide(segment)
    msg = message.msg

    md = f"""
## Turn {turn}
{msg}
"""

    return md
