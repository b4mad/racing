```python
import django_initializer
from telemetry.models import Game, Driver, Car, Track, SessionType, Lap, FastLap
from telemetry.influx import Influx
from telemetry.analyzer import Analyzer
import plotly.express as px
import plotly.io as pio
# pio.renderers.default = "svg"  # comment this line to use interactive plots
import plotly.graph_objects as go

%load_ext autoreload
%autoreload 2

analyzer = Analyzer()
influx = Influx()
```

    The autoreload extension is already loaded. To reload it, use:
      %reload_ext autoreload



```python
measurement = "fast_laps"
bucket = "fast_laps"
# measurement = "laps_cc"
# bucket = "racing"
start = "-10y"
session_df = influx.session_df("1681021274", measurement=measurement, bucket=bucket, start=start)
```


```python
df.info()
```

    <class 'pandas.core.frame.DataFrame'>
    Index: 39727 entries, 0 to 46871
    Data columns (total 29 columns):
     #   Column               Non-Null Count  Dtype
    ---  ------               --------------  -----
     0   result               39727 non-null  object
     1   table                39727 non-null  int64
     2   _start               39727 non-null  datetime64[ns, tzlocal()]
     3   _stop                39727 non-null  datetime64[ns, tzlocal()]
     4   _time                39727 non-null  datetime64[ns, tzlocal()]
     5   CarModel             39727 non-null  object
     6   CurrentLap           39727 non-null  object
     7   GameName             39727 non-null  object
     8   SessionId            39727 non-null  object
     9   SessionTypeName      39727 non-null  object
     10  TrackCode            39727 non-null  object
     11  _measurement         39727 non-null  object
     12  host                 39727 non-null  object
     13  topic                39727 non-null  object
     14  user                 39727 non-null  object
     15  Brake                39727 non-null  float64
     16  Clutch               39727 non-null  float64
     17  CurrentLapIsValid    39727 non-null  bool
     18  CurrentLapTime       39727 non-null  float64
     19  DistanceRoundTrack   39727 non-null  float64
     20  Gear                 39727 non-null  float64
     21  Handbrake            39727 non-null  float64
     22  LapTimePrevious      39727 non-null  float64
     23  PreviousLapWasValid  39727 non-null  bool
     24  Rpms                 39727 non-null  float64
     25  SpeedMs              39727 non-null  float64
     26  SteeringAngle        39727 non-null  float64
     27  Throttle             39727 non-null  float64
     28  id                   39727 non-null  object
    dtypes: bool(2), datetime64[ns, tzlocal()](3), float64(11), int64(1), object(12)
    memory usage: 8.6+ MB



```python
df = session_df.copy()

def lap_fig(df):
    fig = go.Figure()

    fig.add_scatter(
        x=df["_time"],
        y=df["DistanceRoundTrack"],
        marker=dict(size=1),
        name="SpeedMsNormalized",
    )
    return fig

lap_fig(df).show()
```
