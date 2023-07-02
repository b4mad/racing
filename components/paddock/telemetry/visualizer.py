import plotly.graph_objects as go


def telemetry_for_fig(segment, track_length=None):
    if segment.start > segment.end:
        # add track_length to all distances that are less than start
        df = segment.telemetry.copy()
        if track_length is None:
            track_length = df["DistanceRoundTrack"].max()
            print(f"track_length: {track_length}")
        df["DistanceRoundTrack"] = df["DistanceRoundTrack"].apply(
            lambda x: x + track_length if x < segment.start else x
        )
        return df
    return segment.telemetry


def features_for_fig(segment, track_length, features):
    if segment.start > segment.end:
        features = features.copy()
        for key in ["start", "end", "max_start", "max_end"]:
            value = features[key]
            if value < segment.start:
                # print(f"adding track_length to {key} {value} -> {value + track_length}")
                features[key] = value + track_length
    return features


def lap_fig(df, mode=None, columns=["Throttle", "Brake"], fig=None, full_range=False):
    fig = fig or go.Figure()
    # fig = fig or go.Figure(layout=go.Layout(
    #     autosize=False,
    #     width=800,  # specify the width in pixels
    #     height=600  # specify the height in pixels
    # ))

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

    # Set the range of the x-axis and the distance between tick marks
    # set start to the nearest 100 meters
    if not full_range:
        start = df["DistanceRoundTrack"].min()
        start = start - (start % 100)
        # end = df["DistanceRoundTrack"].max()
        # if end - start < 400:
        #     end = start + 400
        end = start + 1000
        x_range = [start, end]
        fig.update_xaxes(range=x_range, dtick=100)

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
    return fig


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
