import dash
import dash_bootstrap_components as dbc
from dash import html
from telemetry.models import Driver, Coach

from django_plotly_dash import DjangoDash

app = DjangoDash("Pitcrew", serve_locally=True, add_bootstrap_links=True)


app.layout = html.Div(
    [
        dbc.Alert("This is an alert", id="base-alert", color="primary"),
        dbc.Switch(
            id="power-switch",
            label="Enabled",
            value=False,
        ),
        html.Div(id="power-state"),
    ]
)


@app.expanded_callback(
    dash.dependencies.Output("base-alert", "children"),
    [dash.dependencies.Input("power-switch", "value")],
)
def power_state(power, session_state=None, **kwargs):
    if not session_state:
        return "No session state"

    driver = Driver.objects.get(pk=session_state["driver_pk"])
    coach = Coach.objects.get_or_create(driver=driver)[0]

    coach.enabled = power
    coach.save()

    return f"Driver: {driver.name} - Enabled: {coach.enabled} - Status: '{coach.status}' - Error: '{coach.error}'"
