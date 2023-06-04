import plotly.graph_objects as go


def lap_fig(df, mode=None, columns=["Throttle", "Brake"], fig=None):
    fig = fig or go.Figure()

    for column in columns:
        color = "red"
        if column == "Throttle":
            color = "green"
        fig.add_scatter(
            x=df["DistanceRoundTrack"],
            y=df[column],
            marker=dict(size=1),
            mode=mode,
            name=column,
            line=dict(color=color),
            showlegend=True,
        )
    return fig


def fig_add_shape(fig, color="black", **kwargs):
    default = dict(
        type="rect",
        xref="x",
        yref="y",
        x0=0,
        y0=0,
        x1=0,
        y1=1,
        line=dict(color=color, width=2, dash="dot"),
    )
    args = {**default, **kwargs}
    fig.add_shape(**args)


def fig_add_features(fig, features, color="red"):
    fig_add_shape(fig, x0=features["start"], x1=features["end"], color=color)
    fig_add_shape(
        fig,
        x0=features["max_start"],
        y0=features["max_low"],
        x1=features["max_end"],
        y1=features["max_high"],
        color=color,
    )
    fig_add_shape(
        fig,
        type="line",
        x0=features["max_start"],
        y0=features["force"],
        x1=features["max_end"],
        y1=features["force"],
        line=dict(color="yellow", width=2),
    )
