import logging

# import matplotlib.pyplot as plt
# import seaborn as sns
import numpy as np
import pandas as pd
import scipy

from .influx import Influx


class FastLapAnalyzerV1:
    def __init__(self, laps):
        self.influx = Influx()
        self.laps = laps

    def analyze(self):
        for lap in self.laps:
            logging.info(
                f"\t{lap.session.session_id} - {lap.pk} : length: {lap.length} time: {lap.time} number: {lap.number} "
            )

        game = self.laps[0].session.game
        car = self.laps[0].car

        if game.name == "RaceRoom":
            logging.info("RaceRoom not supported, because no SteeringAngle")
            return
        if game.name == "Assetto Corsa Competizione":
            logging.info("Assetto Corsa Competizione not supported, because no SteeringAngle")
            return
        if car.name == "Unknown":
            logging.info(f"Car {car.name} not supported, skipping")
            return

        # Construct a dictionary that will store the data
        features = [
            "Brake",
            "Throttle",
            "SteeringAngle",
            "Gear",
            "DistanceRoundTrack",
            "SpeedMs",
            "CurrentLapTime",
        ]
        feature_values = {}
        for feature in features:
            feature_values[feature] = []

        # Loop over the SessionIds for the n fastest laps
        # for i,session in enumerate(np.unique(session_list)):
        for lap in self.laps:
            logging.info(f"Getting data for SessionId: {lap.session.session_id} / {lap.number}")
            # format datetime to flux format
            start = lap.start.strftime("%Y-%m-%dT%H:%M:%SZ")
            end = lap.end.strftime("%Y-%m-%dT%H:%M:%SZ")
            query = f"""
                from(bucket: "racing")
                |> range(start: {start}, stop: {end})
                |> filter(fn: (r) => r["_measurement"] == "laps_cc")
                |> filter(fn: (r) => r["SessionId"] == "{lap.session.session_id}")
                |> filter(fn: (r) => r["GameName"] == "{lap.session.game.name}")
                |> filter(fn: (r) => r["CarModel"] == "{lap.car.name}")
                |> filter(fn: (r) => r["TrackCode"] == "{lap.track.name}")
                |> filter(fn: (r) => r["CurrentLap"] == "{lap.number}")
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"], desc: false)
            """
            # Open the data frame corresponding to session
            try:
                # print(query)
                df = self.influx.query_api.query_data_frame(query=query)
                # print(df["SteeringAngle"].to_string())
                for feature in features:
                    feature_values[feature].append(df[feature].values)
            except Exception as e:
                logging.error(f"Could not get data for SessionId: {lap.session.session_id} / {lap.number} / {e}")
                continue

        if len(feature_values["Brake"]) == 0:
            logging.error("No data found")
            return

        # Define the maximal size of all SteeringAngle arrays
        # print(feature_values["SteeringAngle"])
        max_number_of_datapoints = max([s.size for s in feature_values["SteeringAngle"]])

        # Define a dictionnary that will store the data
        # we need a dictionnary that contains arrays with all the same size,
        # rather than the previous dictionnary that was containing lists
        data_arrays = {}
        for feature in features:
            data_arrays[feature] = np.zeros((len(self.laps), max_number_of_datapoints))

        # Better to have ones for Throttle instead of zeros
        data_arrays["Throttle"] = np.ones((len(self.laps), max_number_of_datapoints))

        # Fill the dictionnary with data
        for i in range(len(self.laps)):
            for feature in features:
                data_arrays[feature][i][: feature_values[feature][i].size] = feature_values[feature][i]

        # Do the average of all data in the dictionnary
        # over the n fastest laps
        # and store it in a new dictionnary
        # FIXME: not sure if this is the best way to find the average signal

        av_data_arrays = {}
        for feature in features:
            av_data_arrays[feature] = np.mean(data_arrays[feature], axis=0)

        # for readibility, define a variable that store the average SteeringAngle array
        steer = av_data_arrays["SteeringAngle"]

        # normalize the SteeringAngle array between -1 and 1
        steer = steer / np.max(np.abs(steer))

        # smooth the data
        window_length = 60  # 60 points corresponds to 1 seconds
        steer_smooth = scipy.signal.savgol_filter(steer, window_length, 2)
        # plt.plot(steer_smooth, label="SteeringAngle")
        steer = steer_smooth

        # Define threshold to select major turns, which means abs(SteeringAngle) > threshold
        threshold = 0.2
        # Find extrama in SteeringAngle
        # Mask 1 gives the indices where SteerinAngle is above thresold : each major turn
        msk1 = np.where(np.abs(steer) > threshold)

        # Mask 2 gives the indices of the end of a major turn
        # which means when the indices giving the major turns are separeted by 10 or more
        idx = np.arange(steer.size)[msk1]
        idx_diff = idx[1:] - idx[:-1]
        msk2 = np.concatenate(([0], np.where(idx_diff > 10)[0], [idx_diff.size - 1]))

        # Define the list that will store the extrama indices
        extrema_idx = []

        # Mask 3 gives the indices of the center of each major turn
        for i, m in enumerate(msk2[:-1]):
            # select SteeringAngle for the i turn
            steer_tmp = steer[idx[msk2][i] : idx[msk2][i + 1]]
            if steer_tmp.size:
                # find index of the extrema of SteeringAngle
                extrema_idx_tmp = np.argmax(np.abs(steer_tmp))
                # add idx offset to find the index in the full SteeringAngle array
                extrema_idx_truth = extrema_idx_tmp + idx[msk2][i]
                # add to list
                extrema_idx.append(extrema_idx_truth)

        extrema_idx = np.array(extrema_idx)

        # Find the begining and end of each segment : center between two major turns
        center_idx = ((extrema_idx[1:] + extrema_idx[:-1]) / 2).astype("int32")
        center_idx = np.concatenate(([0], center_idx, [steer.size - 1]))

        # # Plot the Averaged SteeringAngle, and show the identification of major turns
        # plt.rcParams["figure.figsize"] = (25, 10)
        # plt.plot(steer, label="SteeringAngle")
        # plt.plot(idx, steer[msk1], "x", label="Major turns")
        # plt.plot(idx[msk2], steer[msk1][msk2], "o", label="End of major turns", markersize="10")
        # plt.plot(
        #     np.arange(steer.size)[extrema_idx],
        #     steer[extrema_idx],
        #     "o",
        #     label="Center of major turn",
        #     markersize="15",
        # )
        # plt.plot(
        #     np.arange(steer.size)[center_idx],
        #     steer[center_idx],
        #     "o",
        #     label="Center between two major turns",
        #     markersize="15",
        # )
        # plt.legend(fontsize=18)
        # plt.show()
        print(f"Number of major turns: {len(extrema_idx)}")

        # Build the segment dictionnary that contains a list for each data entry
        # these lists gather the data for each turn
        track_segment_count = center_idx.size - 1

        # initialize dictionnary
        segment_data = {}
        for feature in features:
            segment_data[feature] = []

        # fill the dictionnary
        for i in range(track_segment_count):
            for feature in features:
                segment_data[feature].append(av_data_arrays[feature][center_idx[i] : center_idx[i + 1]])

        track_info = []
        for i in range(track_segment_count):
            track_info.append(
                {
                    "start": segment_data["DistanceRoundTrack"][i][0],
                    "end": segment_data["DistanceRoundTrack"][i][-1],
                }
            )

        # Average DistanceRoundTrack when brake is pressed the first time
        for i in range(track_segment_count):
            seg = np.where(segment_data["Brake"][i] > 0)
            if seg[0].size > 0:
                j = seg[0][0]
                track_info[i]["brake"] = segment_data["DistanceRoundTrack"][i][j]
            else:
                track_info[i]["brake"] = 0

        # Average brake force during the turn
        for i in range(track_segment_count):
            track_info[i]["force"] = segment_data["Brake"][i].max()

        # Average value of gear at the middle of the turn
        for i in range(track_segment_count):
            track_info[i]["gear"] = av_data_arrays["Gear"][extrema_idx][i]

        # Average lowest value of speed during the turn
        for i in range(track_segment_count):
            track_info[i]["speed"] = av_data_arrays["SpeedMs"][extrema_idx][i]

        # Average value of distance when the brake force is at maximum
        # FIXME: this is not the right way to do it, we want the distance when the brake force starts to decrease
        for i in range(track_segment_count):
            j = np.argmax(segment_data["Brake"][i])
            track_info[i]["stop"] = segment_data["DistanceRoundTrack"][i][j]

        # Average DistanceRoundTrack when the throttle is pressed again during the turn
        for i in range(track_segment_count):
            seg = np.where(segment_data["Throttle"][i] == segment_data["Throttle"][i].min())
            if seg[0].size > 0:
                j = seg[0][-1]
                track_info[i]["accelerate"] = segment_data["DistanceRoundTrack"][i][j]

        # convert track_info, which is an array of dict, to a pandas dataframe
        df = pd.DataFrame(track_info)
        logging.info(df.style.format(precision=1).to_string())
        return track_info
