import statistics

import pandas as pd

# import numpy as np
from scipy.stats import zscore


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
        self._other_features = []
        self.telemetry = pd.DataFrame()
        self._start = 0  # Start distance
        self._end = 0  # End distance
        self.turn = 0  # Turn number
        self.time = 0.0  # Time in seconds
        self.track_length = 0  # Track length in meters

        self.previous_segment = None
        self.next_segment = None

        # added by history to store live data
        self.live_telemetry = []
        self.live_telemetry_frames = []
        self.live_features = {
            "brake": [],
            "throttle": [],
            "gear": [],
            "other": [],
        }

    def log_debug(self, msg):
        if self.history:
            self.history.log_debug(msg)

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

    def offset_distance(self, distance, seconds=0.0):
        return self.history.offset_distance(distance, seconds=seconds)

    def approach_speed(self):
        if self.type == "brake":
            return self.brake_feature("approach_speed")
        if self.type == "throttle":
            return self.throttle_feature("approach_speed")

    def add_features(self, features, type):
        if type == "brake":
            self._brake_features.append(features)
        elif type == "throttle":
            self._throttle_features.append(features)
        elif type == "gear":
            self._gear_features.append(features)
        elif type == "other":
            self._other_features.append(features)
        else:
            raise ValueError(f"unknown type {type}")

    def init_live_features_from_segment(self, segment):
        for type, features in segment.live_features.items():
            self.live_features[type] = features
            # self.add_live_features(features, type=type)

    def add_live_features(self, features, type):
        if type not in self.live_features:
            self.live_features[type] = []
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

    def other_features(self):
        if len(self._other_features) > 0:
            return self._other_features[-1]
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

    def gear_distance(self, gear_n=None):
        if gear_n and gear_n > 10:
            return None
        gear_n = gear_n or self.gear()
        if gear_n:
            distance_gear = self.gear_feature("distance_gear")
            # find the distance for gear_n
            for distance, gear in distance_gear.items():
                if gear == gear_n:
                    return int(distance)
            return self.gear_distance(gear_n + 1)
        return None

    def gear(self):
        gear = self.gear_feature("gear")
        if gear:
            return int(gear)
        return None

    def turn_in(self):
        return int(self.brake_feature("max_end"))

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
        value = self.throttle_feature("max_end")
        if value:
            return int(value)
        return None

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
        # if len(self.live_features["gear"]) < 3:
        #     return 0
        # score driver between 0 and 1
        delta = self.avg_driver_delta()
        if delta < 0:
            return 1
        if delta < 1:
            return 0.5
        return 1

    def avg_driver_delta(self):
        # sector_lap_times = self.feature_values(n=3, feature="sector_lap_time", type="other")
        # # remove 0.0 values
        # sector_lap_times = [x for x in sector_lap_times if x > 0.0]
        avg_sector_lap_time = self.avg_feature(n=3, feature="sector_lap_time", type="other")
        # avg_sector_time = self.avg_feature(n=3, feature="sector_time", type="other")

        if avg_sector_lap_time is None:
            return 10_000

        # return avg_sector_lap_time
        return avg_sector_lap_time - self.time

    def driver_delta(self):
        sector_lap_times = self.feature_values(feature="sector_lap_time", type="other")
        # remove 0 values
        sector_lap_times = [x for x in sector_lap_times if x > 0.0]

        # remove outliers
        low_threshold = self.time * 0.9
        filtered_sector_lap_times = [x for x in sector_lap_times if x >= low_threshold]

        if len(filtered_sector_lap_times) == 0:
            return 10_000
        min_sector_lap_time = min(filtered_sector_lap_times)

        # return avg_sector_lap_time
        delta = min_sector_lap_time - self.time
        return delta

    def feature_values(self, n=0, feature="feature_to_query", type="type_of_feature_set"):
        if type not in self.live_features:
            self.log_debug(f"no {type} features")
            return []
        features = self.live_features[type]
        if n and len(features) <= n:
            return []

        values = []
        for i in range(-1, -len(features), -1):
            value = features[i].get(feature)
            if value and value is not None:
                values.append(value)
            if n and len(values) == n:
                break

        if n and len(values) < n:
            return []
        return values

    def avg_feature(self, n=0, feature="feature_to_query", type="type_of_feature_set"):
        values = self.feature_values(n=n, feature=feature, type=type)
        self.log_debug(f"{type} {feature} values: {values}")

        if len(values) == 0:
            return None

        # 1. Using Z-score to remove outliers
        z_scores = zscore(values)
        threshold = 1  # ChatGPT suggested 3
        values_clean = [x for x, z in zip(values, z_scores) if abs(z) < threshold]

        # 2. Using IQR to remove outliers
        # Q1 = np.percentile(values, 25)
        # Q3 = np.percentile(values, 75)
        # IQR = Q3 - Q1
        # lower_bound = Q1 - (1.5 * IQR)
        # upper_bound = Q3 + (1.5 * IQR)
        # values_clean = [x for x in values if x >= lower_bound and x <= upper_bound]

        self.log_debug(f"{type} {feature} values wo/outliers: {values_clean}")
        # return mean gear
        if values_clean:
            return statistics.mean(values_clean)
        else:
            # if values_clean is empty, either all values are the same or there is only one value
            return values[0]

    def session_laps(self):
        return len(self.live_telemetry_frames)

    def brake_point_diff(self):
        bp = self.brake_point()
        a_bp = self.avg_brake_start()
        if bp and a_bp:
            return abs(a_bp - bp)
        return 99_999

    def apex_diff(self):
        value = self.apex()
        avg_value = self.avg_apex()
        self.log_debug(f"apex: {value} avg: {avg_value}")
        if value and avg_value:
            return abs(avg_value - value)
        return 99_999

    def gear_diff(self):
        value = self.gear()
        avg_value = self.avg_gear()
        self.log_debug(f"gear: {value} avg: {avg_value}")
        if value and avg_value:
            return abs(avg_value - value)
        return 99_999

    def coach_brake_force(self):
        last_brake_force = self.avg_brake_force()
        if last_brake_force is None:
            return False
        force_diff = last_brake_force - self.brake_force()
        force_diff_abs = abs(force_diff)
        if force_diff_abs > 0.3:
            return False

        # no more coaching needed
        return True
        #     new_fragments.append(force_fragment)
        # elif force_diff > 0.1:
        #     new_fragments.append("a bit less")
        # elif force_diff < -0.1:
        #     new_fragments.append("a bit harder")

    def coach_turn_in(self):
        value = self.brake_feature("max_end")
        avg_value = self.avg_feature(n=0, feature="max_end", type=self.type)
        if avg_value is None or value is None:
            return False
        diff = avg_value - value
        diff_abs = abs(diff)
        if diff_abs > 20:
            return False
        # no more coaching needed
        return True

    def coach_brake_point(self):
        if self.brake_point_diff() > 30:
            return False
        return True

    def coach_gear(self):
        if self.gear_diff() > 0.5:
            return False
        return True

    def coach_apex(self):
        if self.apex_diff() > 10:
            return False
        return True

    def coach_throttle_force(self):
        last_throttle_force = self.avg_throttle_force()
        if last_throttle_force is None:
            return False
        force_diff = last_throttle_force - self.throttle_force()
        force_diff_abs = abs(force_diff)
        if force_diff_abs > 0.3:
            return False

        # no more coaching needed
        return True

    def score_generic(self, avg_value, value, range={}):
        range = range or {
            0.3: 0,
            0.2: 0.5,
            0.1: 0.75,
        }
        if avg_value is None or value is None:
            return 0
        diff = avg_value - value
        diff_abs = abs(diff)
        for key, score in range.items():
            if diff_abs > key:
                return score
        return 1

    def score_brake_point(self):
        avg_value = self.avg_brake_start()
        value = self.brake_point()
        range = {
            30: 0,
            20: 0.5,
            10: 0.75,
        }
        return self.score_generic(avg_value, value, range)

    def score_brake_force(self):
        avg_value = self.avg_brake_force()
        value = self.brake_force()
        return self.score_generic(avg_value, value)

    def score_gear(self):
        avg_value = self.avg_gear()
        value = self.gear()
        range = {
            1: 0,
            0.5: 0.5,
            0.1: 0.75,
        }
        return self.score_generic(avg_value, value, range)

    def score_turn_in(self):
        value = self.brake_feature("max_end")
        avg_value = self.avg_feature(n=0, feature="max_end", type=self.type)

        range = {
            20: 0,
            10: 0.5,
            5: 0.75,
        }
        return self.score_generic(avg_value, value, range)

    def score_throttle_force(self):
        avg_value = self.avg_throttle_force()
        value = self.throttle_force()
        range = {
            0.3: 0,
            0.2: 0.5,
            0.1: 0.75,
        }
        return self.score_generic(avg_value, value, range)

    def score_apex(self):
        avg_value = self.avg_apex()
        value = self.apex()
        range = {
            20: 0,
            10: 0.5,
            5: 0.75,
        }
        return self.score_generic(avg_value, value, range)
