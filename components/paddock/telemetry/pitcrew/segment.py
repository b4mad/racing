import pandas as pd


class Segment:
    def __init__(self, history, **kwargs):
        self.telemetry_features = []
        for key, value in kwargs.items():
            self[key] = value
        self.history = history

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def features(self, key, mark="brake"):
        return self[f"{mark}_features"].get(key, None)

    def add_features(self, features):
        self.telemetry_features.append(features)

    def has_last_features(self, mark="brake"):
        if self.telemetry_features:
            if self.telemetry_features[-1].get(f"{mark}_features", False):
                return True
        return False

    def last_features(self, key, mark="brake"):
        if self.telemetry_features:
            f = self.telemetry_features[-1].get(f"{mark}_features", {})
            return f.get(key, None)
        return None

    def brake_features(self, key):
        return self.features(key, mark="brake")

    def last_brake_features(self, key):
        return self.last_features(key, mark="brake")

    def throttle_features(self, key):
        return self.features(key, mark="throttle")

    def last_throttle_features(self, key):
        return self.last_features(key, mark="throttle")

    def gear_features(self, key):
        return self.features(key, mark="gear")

    def last_gear_features(self, key):
        return self.last_features(key, mark="gear")

    def avg_gear(self, n=3):
        return self.avg_feature(n=n, feature="gear", mark="gear_features")

    def avg_brake_force(self, n=3):
        return self.avg_feature(n=n, feature="force", mark="brake_features")

    def avg_throttle_force(self, n=3):
        return self.avg_feature(n=n, feature="force", mark="throttle_features")

    def avg_throttle_start(self, n=3):
        return self.avg_feature(n=n, feature="start", mark="throttle_features")

    def avg_brake_start(self, n=3):
        return self.avg_feature(n=n, feature="start", mark="brake_features")

    def avg_feature(self, n=3, feature="gear", mark="gear_features"):
        if len(self.telemetry_features) <= n:
            return None
        # collect the last n entries from telemetry_features, where the 'gear' key is not None
        features_collection = []
        for i in range(-1, -len(self.telemetry_features), -1):
            features = self.telemetry_features[i].get(mark)
            if features and features.get(feature) is not None:
                features_collection.append(features)
            if len(features_collection) == n:
                break

        # calculate the average gear
        feature_values = [f.get(feature) for f in features_collection]
        self.history.log_debug(f"{mark} {feature} values: {feature_values}")

        # Create pandas series from the data
        data = pd.Series(feature_values)
        # Compute EMA
        ema = data.ewm(span=3, adjust=False).mean()
        return ema.iloc[-1]

        # return median gear
        # return statistics.median(gears)
