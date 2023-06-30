import logging

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.signal import argrelextrema, savgol_filter
from sklearn.cluster import KMeans


class Analyzer:
    def __init__(self):
        pass

    def meters_section(self, df):
        first = df.iloc[0]["DistanceRoundTrack"]
        last = df.iloc[-1]["DistanceRoundTrack"]
        return last - first

    def split_sectors(
        self, df, threshold=None, min_length_throttle_below_threshold=50, min_distance_between_sectors=50
    ):
        if threshold is None:
            threshold = df["Throttle"].max() * 0.98
        # Step 1: Find all rows where Throttle starts to drop below the threshold
        start = df[(df["Throttle"] < threshold) & (df["Throttle"].shift(1) >= threshold)].index
        end = df[(df["Throttle"] < threshold) & (df["Throttle"].shift(-1) >= threshold)].index
        max_distance = df["DistanceRoundTrack"].max()

        if len(start) == 0:
            logging.error(f"No sectors found threshold: {threshold} min_length: {min_length_throttle_below_threshold}")
            return [df]

        if len(start) != len(end):
            logging.error(f"start and end are not the same length: {len(start)} {len(end)}")
            return [df]

        # combine start and end into sector dicts
        start_idx = 0
        end_idx = 0
        # find the first end that is larger than the first start
        for i in range(len(end)):
            if end[i] > start[start_idx]:
                end_idx = i
                break

        sectors = []
        for i in range(len(start)):
            sector = {}
            sector["start"] = start[start_idx]
            sector["end"] = end[end_idx]
            sector["length_throttle_below_threshold"] = (sector["end"] - sector["start"]) % max_distance
            sectors.append(sector)
            start_idx += 1
            end_idx = (end_idx + 1) % len(end)

        # remove all sectors that are too short
        sectors = [
            sector
            for sector in sectors
            if sector["length_throttle_below_threshold"] > min_length_throttle_below_threshold
        ]

        # combine sectors that are too short with the previous sector
        remove_indices = []
        for i, sector in enumerate(sectors):
            prev_index = i - 1 % len(sectors)
            prev_sector = sectors[prev_index]
            distance_between = (sector["start"] - prev_sector["end"]) % max_distance
            if distance_between < min_distance_between_sectors:
                # append to previous sector
                sector["start"] = prev_sector["start"]
                remove_indices.append(i)
        sectors = [sector for i, sector in enumerate(sectors) if i not in remove_indices]

        # set the start and end of the sectors to the middle between the start and end
        for i, sector in enumerate(sectors):
            prev_index = i - 1 % len(sectors)
            prev_sector = sectors[prev_index]
            prev_end = prev_sector["end"]
            start = sector["start"]
            distance_between = (start - prev_end) % max_distance

            new_sector_start = int(prev_end + (distance_between / 2) % max_distance)
            sector["start"] = new_sector_start
            prev_sector["end"] = new_sector_start - 1

        # recalculate the length of the sectors
        for i, sector in enumerate(sectors):
            sector["length"] = int((sector["end"] - sector["start"]) % max_distance)
            del sector["length_throttle_below_threshold"]

        return sectors

    def extract_sector_frames(self, df, sectors):
        sector_df = []
        for sector in sectors:
            start = sector["start"]
            end = sector["end"]
            sector_df = self.section_df(df, start, end)
            sector["df"] = sector_df
        return sector_df

    def section_df(self, track_df, start, end):
        # Calculate the maximum DistanceRoundTrack value
        max_distance = track_df["DistanceRoundTrack"].max()

        if end < start:
            # Wrap around the max_distance
            first_part = track_df[
                (track_df["DistanceRoundTrack"] >= start) & (track_df["DistanceRoundTrack"] <= max_distance)
            ]
            second_part = track_df[(track_df["DistanceRoundTrack"] >= 0) & (track_df["DistanceRoundTrack"] <= end)]
            sector_df = pd.concat([first_part, second_part], axis=0).reset_index(drop=True)
        else:
            sector_df = track_df[
                (track_df["DistanceRoundTrack"] >= start) & (track_df["DistanceRoundTrack"] <= end)
            ].reset_index(drop=True)

        return sector_df

    def sector_type(self, sector_df, brake_threshold=0.1):
        # Rule 1: If the brake column is always below a threshold then throttle
        if sector_df["Brake"].max() < brake_threshold:
            return "throttle"
        # Rule 2: Otherwise brake
        else:
            return "brake"

    def brake_window(self, sector_df, threshold=0.1):
        above_threshold = sector_df[sector_df["Brake"] > threshold]
        below_threshold = sector_df[sector_df["Brake"] <= threshold]

        if not above_threshold.empty:
            start = above_threshold.iloc[0]["DistanceRoundTrack"]
        else:
            start = None

        if start is not None and not below_threshold.empty:
            end_section = below_threshold[below_threshold["DistanceRoundTrack"] > start]
            if not end_section.empty:
                end = end_section.iloc[0]["DistanceRoundTrack"]
            else:
                end = sector_df.iloc[-1]["DistanceRoundTrack"]
            # end = below_threshold[below_threshold["DistanceRoundTrack"] > start].iloc[0][
            #     "DistanceRoundTrack"
            # ]
        else:
            end = None

        return start, end

    def throttle_window(self, sector_df, threshold=0.9):
        below_threshold = sector_df[sector_df["Throttle"] <= threshold]
        above_threshold = sector_df[sector_df["Throttle"] > threshold]

        if not below_threshold.empty:
            start = below_threshold.iloc[0]["DistanceRoundTrack"]
        else:
            start = None

        if start is not None and not above_threshold.empty:
            end_section = above_threshold[above_threshold["DistanceRoundTrack"] > start]
            if not end_section.empty:
                end = end_section.iloc[0]["DistanceRoundTrack"]
            else:
                end = sector_df.iloc[-1]["DistanceRoundTrack"]
        else:
            end = None

        return start, end

    def extract_window_start_end(self, sector_df, threshold, comparison_operator):
        if comparison_operator == "greater_than":
            above_threshold = sector_df[sector_df["Brake"] > threshold]
            below_threshold = sector_df[sector_df["Brake"] <= threshold]
        elif comparison_operator == "less_than":
            above_threshold = sector_df[sector_df["Throttle"] >= threshold]
            below_threshold = sector_df[sector_df["Throttle"] < threshold]
        else:
            raise ValueError("Invalid comparison_operator")

        if not above_threshold.empty:
            window_start = above_threshold.iloc[0]["DistanceRoundTrack"]
        else:
            window_start = None

        if window_start is not None and not below_threshold.empty:
            window_end = below_threshold[below_threshold["DistanceRoundTrack"] > window_start].iloc[0][
                "DistanceRoundTrack"
            ]
        else:
            window_end = None

        return window_start, window_end

    def get_average(self, search_df, column="Brake", max=True):
        if max:
            high = abs(round(search_df[column].max(), 2))
            low = high * 0.9
            start = search_df[search_df[column] > low].index.min()
            end = search_df[search_df[column] > low].index.max()
        else:
            low = abs(round(search_df[column].min(), 2))
            high = low * 1.1
            if low <= 0.1:
                high = 0.1
            start = search_df[search_df[column] < high].index.min()
            end = search_df[search_df[column] < high].index.max()

        return start, end

    def top_bin(self, df, column="Brake"):
        bins = pd.cut(df[column], bins=[x / 10 for x in range(11)], include_lowest=True)
        if column == "Brake":
            bin_counts = bins.value_counts().drop(bins.cat.categories[:1])
        else:
            bin_counts = bins.value_counts().drop(bins.cat.categories[-1:])
        ascending = column == "Throttle"
        largest_two_bins = bin_counts.nlargest(2).sort_index(ascending=ascending)

        first_bin, second_bin = largest_two_bins.index
        first_count, second_count = largest_two_bins.values
        if first_count and second_count:
            if first_bin.left == second_bin.right:
                # both top bins are adjacent
                return second_bin.left, first_bin.right
            else:
                # top bins are not adjacent
                return first_bin.left, first_bin.right
        elif first_count:
            return first_bin.left, first_bin.right
        elif second_count:
            return second_bin.left, second_bin.right
        else:
            if column == "Brake":
                return 0, 0.1
            return 0.9, 1

    def brake_features(self, sector_df, brake_threshold=0.1):
        start, end = self.brake_window(sector_df, threshold=brake_threshold)

        features = {}

        if start and end:
            features["start"] = start
            features["end"] = end

            brake_df = self.section_df(sector_df, start, end)
            min_force, max_force = self.top_bin(brake_df)
            peak_force_df = brake_df[(brake_df["Brake"] >= min_force) & (brake_df["Brake"] <= max_force)]

            features["max_start"] = peak_force_df["DistanceRoundTrack"].min()
            features["max_end"] = peak_force_df["DistanceRoundTrack"].max()
            features["max_high"] = round(peak_force_df["Brake"].max(), 2)
            features["max_low"] = round(peak_force_df["Brake"].min(), 2)
            features["force"] = round(peak_force_df["Brake"].mean(), 2)

        return features

    def throttle_features(self, sector_df, threshold=None):
        if threshold is None:
            threshold = sector_df["Throttle"].max() * 0.98
        start, end = self.throttle_window(sector_df, threshold=threshold)
        features = {}
        if start and end:
            features["start"] = start
            features["end"] = end

            df = self.section_df(sector_df, start, end)

            column = "Throttle"
            min_force, max_force = self.top_bin(df, column=column)

            peak_force_df = df[(df[column] >= min_force) & (df[column] <= max_force)]

            features["max_start"] = peak_force_df["DistanceRoundTrack"].min()
            features["max_end"] = peak_force_df["DistanceRoundTrack"].max()
            features["max_high"] = round(peak_force_df[column].max(), 2)
            features["max_low"] = abs(round(peak_force_df[column].min(), 2))
            features["force"] = abs(round(peak_force_df[column].mean(), 2))

        return features

    def resample(self, input_df, columns=["Brake", "SpeedMs"], method="nearest", freq=1):
        df = input_df.replace({None: np.nan}).dropna(subset=["DistanceRoundTrack"])
        if len(df) == 0:
            return input_df

        min_distance = int(df["DistanceRoundTrack"].min()) + 1
        max_distance = int(df["DistanceRoundTrack"].max())
        target_rows = int(max_distance / freq)

        new_distance_round_track = np.linspace(min_distance, max_distance, target_rows)

        new_distance_round_track = np.round(new_distance_round_track, decimals=2)
        new_distance_round_track[0] = max(new_distance_round_track[0], min_distance)
        new_distance_round_track[-1] = min(new_distance_round_track[-1], max_distance)

        resampled_df = pd.DataFrame({"DistanceRoundTrack": new_distance_round_track})

        for column in columns:
            interp = interp1d(df["DistanceRoundTrack"], df[column], kind=method)
            interpolated_values = interp(new_distance_round_track)

            if np.issubdtype(df[column].dtype, np.integer):
                interpolated_values = np.round(interpolated_values).astype(int)

            resampled_df[column] = interpolated_values

        return resampled_df

    def value_at_distance(self, df, meters, column="SpeedMs"):
        value = df.iloc[(df["DistanceRoundTrack"] - meters).abs().idxmin()][column]
        return value

    def distance_speed_lookup_table(self, lap):
        lookup = self.distance_speed_lookup_table_non_lin(lap)
        monotonic = lookup["CurrentLapTime"].is_monotonic_increasing
        if monotonic:
            logging.debug("distance_speed_lookup_table monotonic")
            return lookup
        else:
            logging.debug("distance_speed_lookup_table NOT monotonic")
            return self.distance_speed_lookup_table_lin(lap)

    def distance_speed_lookup_table_lin(self, lap):
        lap = lap[["DistanceRoundTrack", "CurrentLapTime", "SpeedMs"]].copy()

        # Use numpy linspace to generate evenly spaced float values from 0 to the max of CurrentLapTime
        max_lap_time = lap["CurrentLapTime"].max()
        lap["CurrentLapTime"] = np.linspace(0, max_lap_time, len(lap))

        lap = lap[["DistanceRoundTrack", "CurrentLapTime", "SpeedMs"]]
        lap["DistanceRoundTrack"] = lap["DistanceRoundTrack"].round(1)
        lap["CurrentLapTime"] = lap["CurrentLapTime"].round(3)
        return lap

    def distance_speed_lookup_table_non_lin(self, lap):
        # find the index where the lap starts, thats where CurrentLapTime is minimal
        # only keep the part of the lap after the start
        lap = lap[["DistanceRoundTrack", "CurrentLapTime", "SpeedMs"]].copy()
        lap_start = lap["CurrentLapTime"].idxmin()

        lap.loc[:lap_start, "CurrentLapTime"] = (
            lap.loc[:lap_start, "DistanceRoundTrack"] / lap.loc[:lap_start, "SpeedMs"]
        )
        lap = lap[["DistanceRoundTrack", "CurrentLapTime", "SpeedMs"]]
        lap["DistanceRoundTrack"] = lap["DistanceRoundTrack"].round(1)
        lap["CurrentLapTime"] = lap["CurrentLapTime"].round(3)
        return lap

    def combine_max_throttle(self, laps):
        df_max = laps[0]
        # fig = lap_fig(df_max, full_range=True)
        # fig.show()
        for df in laps[1:]:
            # fig = lap_fig(df, full_range=True)
            # fig.show()

            df_max_throttle = df_max[["Throttle"]].combine(df[["Throttle"]], np.maximum)
            df_max["Throttle"] = df_max_throttle
            # fig = lap_fig(df_max, full_range=True)
            # fig.show()

        return df_max

        # display(df_max)
        # fig = lap_fig(df_max, full_range=True)
        # fig.show()

    ##### probably not needed anymore

    def split_sectors_old(self, df, threshold=None, min_length=50):
        if threshold is None:
            threshold = df["Throttle"].max() * 0.98
        # Step 1: Find all rows where Throttle starts to drop below the threshold
        start = df[(df["Throttle"] < threshold) & (df["Throttle"].shift(1) >= threshold)].index

        if len(start) == 0:
            logging.debug(f"No sectors found threshold: {threshold} min_length: {min_length}")
            return [df]

        # Step 3: Split the dataframe into sections
        sectors = []
        for i in range(len(start)):
            if i < len(start) - 1:
                sector = df.iloc[start[i] : start[i + 1]]
            else:
                sector = df.iloc[start[i] :]

            below_threshold = sector[sector["Throttle"] < threshold]
            if i and self.meters_section(below_threshold) < min_length:
                # append to previous sector
                sectors[-1] = pd.concat([sectors[-1], sector])
            else:
                sectors.append(sector)

        # check the length of the first sector
        # if its too short, then append it to the append the second sector and remove the second sector
        below_threshold = sectors[0][sectors[0]["Throttle"] < threshold]
        if self.meters_section(below_threshold) < min_length and len(sectors) > 1:
            sectors[0] = pd.concat([sectors[0], sectors[1]])
            sectors.pop(1)

        # Step 4: Return a list of dataframes, one for each section
        return sectors

    def extract_sector_start_end(self, sectors, threshold=0.98, track_length=0, min_length=50):
        sector_start_end = []

        # Calculate the maximum DistanceRoundTrack value of all sectors
        if track_length == 0:
            track_length = max([sector["DistanceRoundTrack"].max() for sector in sectors])

        for i, sector in enumerate(sectors):
            # if i == 0:
            #     prev_sector = sectors[-1]
            # else:
            #     prev_sector = sectors[i - 1]
            # start, end = self.throttle_window(prev_sector, threshold=0.95)
            # last_meter_of_prev_sector = prev_sector.iloc[-1]["DistanceRoundTrack"]
            # logging.debug(f"start: {start} end: {end}, last_meter_of_prev_sector: {last_meter_of_prev_sector}")
            # if start:
            #     delta = int((last_meter_of_prev_sector - end) / 2)
            # else:
            #     delta = 10
            # logging.debug(f"delta: {delta}")
            # first_meter_of_sector = sector.iloc[0]["DistanceRoundTrack"]
            # logging.debug(f"first_meter_of_sector: {first_meter_of_sector}")
            delta = 10

            # Rule 1: A sector N starts delta meters earlier than the first row of a DataFrame
            start = int((sector["DistanceRoundTrack"].iloc[0] - delta) % track_length)

            # Rule 1a: Unless the previous DataFrame for sector N-1 has Throttle input below threshold
            # at the calculated start of N
            if i > 0:
                prev_sector = sectors[i - 1]
                prev_sector_last_row = prev_sector.iloc[-1]
                if prev_sector_last_row["Throttle"] < threshold and prev_sector_last_row["DistanceRoundTrack"] >= start:
                    start = int(prev_sector_last_row["DistanceRoundTrack"])

            # Rule 2: The last sector ends where the first sector starts
            if i == len(sectors) - 1:
                end = int((sectors[0]["DistanceRoundTrack"].iloc[0] - delta - 1) % track_length)
            else:
                end = int(
                    (sectors[i + 1]["DistanceRoundTrack"].iloc[0] - delta - 1) % track_length
                )  # Subtract 11 to make the boundaries exactly one meter apart

            length = int((end - start) % track_length)

            # Merge sectors shorter than the threshold with the previous sector
            if i > 0 and length < min_length:
                sector_start_end[-1]["end"] = end
                sector_start_end[-1]["length"] = (
                    sector_start_end[-1]["end"] - sector_start_end[-1]["start"]
                ) % track_length
            else:
                sector_start_end.append({"start": start, "end": end, "length": length})
        return sector_start_end

    def local_maxima(self, df, column="Gear", points=50):
        return self.local_extrema(df, column, mode="max", points=points)

    def local_minima(self, df, column="Gear", points=50):
        return self.local_extrema(df, column, mode="min", points=points)

    def local_extrema(self, df, column="Gear", mode="min", points=50):
        # https://stackoverflow.com/questions/48023982/pandas-finding-local-max-and-min
        # Find local peaks
        n = points  # number of points to be checked before and after
        # Find local peaks

        if column == "Gear":
            min = df.iloc[argrelextrema(df[column].values, np.less_equal, order=n)[0]][column]
            max = df.iloc[argrelextrema(df[column].values, np.greater_equal, order=n)[0]][column]
        else:
            min = df.iloc[argrelextrema(df[column].values, np.less, order=n)[0]][column]
            max = df.iloc[argrelextrema(df[column].values, np.greater, order=n)[0]][column]

        # select only the indexes of minima and maximma in the original dataframe
        min_max = df.loc[min.index.union(max.index)]
        # # also add the first and last row
        min_max = pd.concat([min_max, df.iloc[[0, -1]]])

        if mode == "min":
            # now find the local minima again
            real = min_max[column][
                (min_max[column].shift(1) >= min_max[column]) & (min_max[column].shift(-1) > min_max[column])
            ]
        else:
            # now find the local maxima again
            real = min_max[column][
                (min_max[column].shift(1) <= min_max[column]) & (min_max[column].shift(-1) < min_max[column])
            ]

        return df.loc[real.index]

    def local_minima_off(self, df, column="Gear"):
        # https://stackoverflow.com/questions/48023982/pandas-finding-local-max-and-min
        # Find local peaks
        # df['max'] = df.Gear[(df.Gear.shift(1) <= df.Gear) & (df.Gear.shift(-1) < df.Gear)]
        # df = in_df.copy()

        min = df[column][(df[column].shift(1) >= df[column]) & (df[column].shift(-1) > df[column])]
        max = df[column][(df[column].shift(1) <= df[column]) & (df[column].shift(-1) < df[column])]

        # select only the indexes of minima in the original dataframe
        min_max = df.loc[min.index.union(max.index)]
        # also add the first and last row
        min_max = pd.concat([min_max, df.iloc[[0, -1]]])

        # now find the local minima again
        real_min = min_max[column][
            (min_max[column].shift(1) >= min_max[column]) & (min_max[column].shift(-1) > min_max[column])
        ]
        return df.loc[real_min.index]

    def extend_lap(self, df, count=2):
        max_distance = df["DistanceRoundTrack"].max()
        df_copy = df.copy()
        for i in range(1, count + 1):
            df2 = df_copy.copy()
            df2["DistanceRoundTrack"] = df2["DistanceRoundTrack"].add(max_distance * i)
            df = pd.concat([df, df2], ignore_index=True)
        return df

    def cluster(self, minima_dfs, n_clusters=None, field="Gear"):
        df = pd.concat(minima_dfs)

        if n_clusters is None:
            # calculate the median of all lengths of all_minima array
            n_clusters = int(np.median([len(m) for m in minima_dfs]))

        # Extract the x and y coordinates of the track
        x = df[[field, "DistanceRoundTrack"]]

        # Fit a k-means model to the data
        kmeans = KMeans(n_clusters=n_clusters, n_init="auto")
        kmeans.fit(x)

        # Predict the cluster labels for each data point
        labels = kmeans.predict(x)
        # Get the centroids of all clusters
        centroids = kmeans.cluster_centers_
        # Convert the centroids to a pandas DataFrame
        centroids_df = pd.DataFrame(centroids, columns=[field, "DistanceRoundTrack"])

        return centroids_df, labels

    def remove_uncorrelated_laps(self, laps, column="SpeedMs", threshold=0.6):
        # remove laps that are too different from the others
        scores = []
        no_laps = len(laps)
        for i in range(len(laps)):
            for j in range(i + 1, len(laps)):
                correlation = laps[i][column].corr(laps[j][column])
                # print(f"{i} {j} {correlation}")
                if correlation < threshold:
                    scores.append(i)
                    scores.append(j)

        # get the most common number
        scores.sort()
        if len(scores) > 0:
            scores = np.array(scores)
            scores = np.bincount(scores)
            # display(scores)
            # max = np.argmax(scores)
            # print(max)
            # get all bins larger than 2
            scores = np.where(scores > no_laps * 0.8)[0]
            # display(scores)
            ignore_laps = scores

            for idx in ignore_laps:
                logging.debug("remove lap: " + laps[idx]["id"].iloc[0])
                # print("remove lap: " + laps[idx]["id"].iloc[0])
        else:
            ignore_laps = []

        # remove all indices from laps where the index is in ignore_laps
        return [laps[i] for i in range(len(laps)) if i not in ignore_laps]

    def drop_decreasing(self, df, column="DistanceRoundTrack"):
        # drop all rows where the distance is decreasing
        # df = df[df[column].diff() > 0]
        cols = [column]
        mon_inc = (df[cols].cummax().diff().fillna(0.1) > 0).all(axis=1)
        return df[mon_inc]

    def make_monotonic(self, distances, points):
        # Iterate over the tracks
        max_distance = distances[0]
        selected_idx = []
        for idx in range(distances.shape[0]):
            # If distance is higher than previous distance, select the point
            if distances[idx] > max_distance:
                selected_idx.append(idx)
                max_distance = distances[idx]

        return distances[selected_idx], points[selected_idx]

    def track_length(self, distances):
        length = 0
        for lap in distances:
            max_distance = lap.max()
            if max_distance > length:
                length = max_distance
        return length

    def resample_(self, distances, points, length):
        delta_distance = 2  # [meter]
        distances = distances.copy()
        points = points.copy()
        resampled_distances = np.arange(0, length, delta_distance)
        x = points[:, 0]
        y = points[:, 1]
        x_n = np.interp(resampled_distances, distances, x, left=np.nan, right=np.nan)
        y_n = np.interp(resampled_distances, distances, y, left=np.nan, right=np.nan)

        return resampled_distances, np.column_stack((x_n, y_n))

    def remove_outliers(self, points):
        # Laps have some extream telemetry message.
        # These outliers need to be filled with nan values.
        #  If yaw angle changes more than a threshold, this point is accepted as extreme
        delta_distance = 2  # [radian]
        threshold = 0.4  # [radian]
        filter_window = 60  # [meter]

        filter_window_index = filter_window / delta_distance
        points = points.copy()

        # If yaw angle is higher than a threshold
        # Fill filter window with nan values
        differences = np.diff(points, axis=0)
        yaw_angles = np.arctan2(differences[:, 0], differences[:, 1])
        mask = ~np.isnan(yaw_angles)
        yaw_angles[mask] = np.unwrap(yaw_angles[mask])
        yaw_changes = np.diff(yaw_angles)
        for point_idx in range(points.shape[0] - 2):
            if abs(yaw_changes[point_idx]) > threshold:
                start = int(max(0, point_idx - filter_window_index))
                end = int(min(points.shape[0] - 1, point_idx + filter_window_index))
                points[start:end, :] = np.nan

        return points

    def merge_track_points(self, distances_a, points_a, length):
        delta_distance = 2  # [meter]
        filter_window = 60
        # filter_order = 2
        filter_window_index = filter_window / delta_distance

        track_distances = []
        track_points = []
        num_samples = int(length / delta_distance)

        # Iterate over sample points
        for point_idx in range(num_samples):
            window_distances = []
            window_x = []
            window_y = []
            # Iterate over the laps
            for lap_idx in range(len(distances_a)):
                distances = distances_a[lap_idx].copy()
                points = points_a[lap_idx].copy()
                # Calculate start and end index of filter window
                start = int(max(0, point_idx - filter_window_index))
                end = int(min(num_samples - 1, point_idx + filter_window_index))
                # Get points in filter window
                window_distances.extend(distances[start:end])
                window_x.extend(points[start:end, 0])
                window_y.extend(points[start:end, 1])

            window_distances = np.array(window_distances)
            window_x = np.array(window_x)
            window_y = np.array(window_y)
            window_distances = window_distances[~np.isnan(window_x)]
            window_y = window_y[~np.isnan(window_x)]
            window_x = window_x[~np.isnan(window_x)]
            # Fit a polynom to points in filter windows
            px = np.polyfit(window_distances, window_x, 2)
            py = np.polyfit(window_distances, window_y, 2)
            fx = np.poly1d(px)
            fy = np.poly1d(py)
            # Calculate the point by using polynomial
            p = np.array([fx(distances[point_idx]), fy(distances[point_idx])])
            track_distances.append(distances[point_idx])
            track_points.append(p)

        return np.array(track_distances), np.array(track_points)

    def yaw_changes(self, points):
        # distances = distances.copy()
        # points = points.copy()
        # Yaw changes can be calculated by track points
        differences = np.diff(points, axis=0)
        yaw_angles = np.arctan2(differences[:, 0], differences[:, 1])
        yaw_angles = np.unwrap(yaw_angles)
        yaw_changes = np.diff(yaw_angles)
        yaw_changes = np.pad(yaw_changes, (0, 2), "constant", constant_values=(0, 0))
        # Yawy changes are filtered with savgol filter.
        yaw_changes = savgol_filter(yaw_changes, 20, 1)
        return yaw_changes

    def track_sections(self, distances, yaw_changes, threshold=0.0051):
        min_threshold = threshold
        threshold = min_threshold

        cw_max = 0
        cw_start_idx = 0
        cw_started = False
        ccw_max = 0
        ccw_started = False
        ccw_start_idx = 0
        str_started = False
        str_max = 0
        str_start_idx = 0
        sections = []

        # Iterate over sample points
        for point_idx in range(20, distances.shape[0]):
            # Check last index
            last_index = point_idx == distances.shape[0] - 1
            # Reset threshold
            if abs(yaw_changes[point_idx]) < min_threshold:
                threshold = min_threshold
            # Check clock wise corner started and ended
            if not cw_started:
                if yaw_changes[point_idx] > threshold:
                    cw_max = 0
                    cw_started = True
                    cw_start_idx = point_idx
            else:
                cw_max = max(cw_max, abs(yaw_changes[point_idx]))
                threshold = max(min_threshold, abs(cw_max / 2))
                if last_index or (yaw_changes[point_idx] <= threshold):
                    cw_started = False
                    sec = {
                        "type": "clock_wise",
                        "start": distances[cw_start_idx],
                        "end": distances[point_idx],
                        "max_yaw_change": cw_max,
                    }
                    sections.append(sec)
            # Check counter clock wise corner started and ended
            if not ccw_started:
                if yaw_changes[point_idx] < -threshold:
                    ccw_max = 0
                    ccw_started = True
                    ccw_start_idx = point_idx
            else:
                ccw_max = max(ccw_max, abs(yaw_changes[point_idx]))
                threshold = max(min_threshold, abs(ccw_max / 2))
                if last_index or (yaw_changes[point_idx] >= -threshold):
                    ccw_started = False
                    sec = {
                        "type": "counter_clock_wise",
                        "start": distances[ccw_start_idx],
                        "end": distances[point_idx],
                        "max_yaw_change": ccw_max,
                    }
                    sections.append(sec)
            # Check straigh section started and ended
            if not str_started:
                if abs(yaw_changes[point_idx]) < threshold:
                    str_max = 0
                    str_started = True
                    str_start_idx = point_idx
            else:
                str_max = max(str_max, yaw_changes[point_idx])
                if last_index or (abs(yaw_changes[point_idx]) >= threshold):
                    str_started = False
                    sec = {
                        "type": "straight",
                        "start": distances[str_start_idx],
                        "end": distances[point_idx],
                        "max_yaw_change": str_max,
                    }
                    sections.append(sec)

        return sections

    # # This function split data for multiple laps
    # def split_laps(self, distances, points, threshold=100):
    #     laps = []
    #     prev_idx = 0
    #     for idx in range(1, distances.shape[0]):
    #         # If DistanceRoundTrack dropped significantly, this is a new lap
    #         passed_start = distances[idx] - distances[idx-1] < -threshold
    #         last_point = (idx == distances.shape[0]-1)
    #         if passed_start or last_point:
    #             lap_distances = distances[prev_idx:idx]
    #             lap_points = points[prev_idx:idx]
    #             lap = {'distances': lap_distances,
    #                 'points': lap_points}
    #             laps.append(lap)
    #             prev_idx = idx
    #     return laps['distances'], laps['points']
