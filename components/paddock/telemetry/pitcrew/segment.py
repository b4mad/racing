import pandas as pd


class Segment:
    def __init__(self, history=None, **kwargs):
        self.telemetry_features = []
        # for key, value in kwargs.items():
        #     self[key] = value
        self.history = history
        self.type = "brake_or_throttle"
        self._brake_features = []
        self._throttle_features = []
        self._gear_features = []
        self.telemetry = pd.DataFrame()
        self._start = 0  # Start distance
        self._end = 0  # End distance
        self.turn = 0  # Turn number

        self.previous_segment = None
        self.next_segment = None

        # added by history to store live data
        self.live_telemetry = []
        self.live_telemetry_frames = []
        self.live_features = {
            "brake": [],
            "throttle": [],
            "gear": [],
        }

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = int(value)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        self._end = int(value)

    def copy_from(self, segment):
        self.start = segment.start
        self.end = segment.end
        self.turn = segment.turn
        self.type = segment.type

    def telemetry_for_fig(self):
        if self.start > self.end:
            # add track_length to all distances that are less than start
            df = self.telemetry.copy()
            df["DistanceRoundTrack"] = df["DistanceRoundTrack"].apply(
                lambda x: x + df["DistanceRoundTrack"].max() if x < self.start else x
            )
            return df
        return self.telemetry

    def track_length(self):
        return self.history.track_length

    def offset_distance(self, distance, seconds=0.0):
        return self.history.offset_distance(distance, seconds=seconds)

    def add_features(self, features, type):
        if type == "brake":
            self._brake_features.append(features)
        elif type == "throttle":
            self._throttle_features.append(features)
        elif type == "gear":
            self._gear_features.append(features)
        else:
            raise ValueError(f"unknown type {type}")

    def init_live_features_from_segment(self, segment):
        for type in ["brake", "throttle", "gear"]:
            for features in segment.live_features[type]:
                self.add_live_features(features, type=type)

    def add_live_features(self, features, type):
        self.live_features[type].append(features)

    def type_brake(self):
        return self.type == "brake"

    def type_throttle(self):
        return self.type == "throttle"

    def brake_features(self):
        if len(self._brake_features) > 0:
            return self._brake_features[-1]
        return {}

    def throttle_features(self):
        if len(self._throttle_features) > 0:
            return self._throttle_features[-1]
        return {}

    def gear_features(self):
        if len(self._gear_features) > 0:
            return self._gear_features[-1]
        return {}

    def brake_feature(self, key):
        return self.brake_features().get(key)

    def throttle_feature(self, key):
        return self.throttle_features().get(key)

    def gear_feature(self, key):
        return self.gear_features().get(key)

    def brake_point(self):
        if self.type == "brake":
            brake_point = self.brake_feature("start")
            if brake_point:
                return int(brake_point)
        return None

    def throttle_point(self):
        if self.type == "throttle":
            brake_point = self.throttle_feature("start")
            if brake_point:
                return int(brake_point)
        return None

    def full_throttle_point(self):
        max_throttle_point = self.throttle_feature("end")
        if max_throttle_point:
            return int(max_throttle_point)

        return None

    def gear(self):
        gear = self.gear_feature("gear")
        if gear:
            return int(gear)
        return None

    def brake_force(self):
        self.brake_feature("force")
        force = self.brake_feature("force")
        if force:
            return force
        return 0

    def throttle_force(self):
        force = self.throttle_feature("force")
        if force:
            return force
        return 0

    def trail_brake(self):
        max_end = self.brake_feature("max_end")
        max_high = self.brake_feature("max_high")
        end = self.brake_feature("end")
        self._tb_reason = f"max_end: {max_end} max_high: {max_high} end: {end}"
        if max_end and max_high and end:
            # y = mx + b
            b = max_high
            x = end - max_end
            m = -1 * (b / x) * 1000
            self._tb_reason += f" m: {m:.2f} len: {int(end - max_end)}"
            # return int(m * 1000)
            if m >= -20:
                if end - max_end >= 40:  # 50 meters
                    if max_high > 0.4:
                        return True
        return False

    def apex(self):
        return self.throttle_feature("max_end")

    def avg_apex(self, n=0):
        return self.avg_feature(n=n, feature="max_end", type="throttle")

    def avg_trail_brake(self, n=0):
        return self.avg_feature(n=n, feature="max_end", type="brake")

    def avg_gear(self, n=0):
        return self.avg_feature(n=n, feature="gear", type="gear")

    def avg_brake_force(self, n=0):
        return self.avg_feature(n=n, feature="force", type="brake")

    def avg_throttle_force(self, n=0):
        return self.avg_feature(n=n, feature="force", type="throttle")

    def avg_throttle_start(self, n=0):
        return self.avg_feature(n=n, feature="start", type="throttle")

    def avg_brake_start(self, n=0):
        return self.avg_feature(n=n, feature="start", type="brake")

    def driver_score(self):
        if len(self.live_features["gear"]) < 3:
            return 0
        # score driver between 0 and 1
        return 1

    def avg_feature(self, n=0, feature="feature_to_query", type="type_of_feature_set"):
        features = self.live_features[type]
        if len(features) <= n:
            return None

        values = []
        for i in range(-1, -len(features), -1):
            value = features[i].get(feature)
            if value and value is not None:
                values.append(value)
            if len(values) == n:
                break

        if len(values) <= n:
            return None

        self.history.log_debug(f"{type} {feature} values: {values}")

        # Create pandas series from the data
        data = pd.Series(values)
        # Compute EMA
        ema = data.ewm(span=3, adjust=False).mean()
        return ema.iloc[-1]

        # return median gear
        # return statistics.median(gears)
