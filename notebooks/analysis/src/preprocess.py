#!/usr/bin/env python
# -*- coding: utf-8 -*-


""" functions to load data from csv
need to :
* load data from csv , combine the different dumps and transform them
* figure out the laps
* split data into laps
* transform from time domain to space domain
"""


import os
import numpy as np
import pathlib
import pandas as pd
from io import StringIO
import logging


log = logging.getLogger("preprocess")
logging.basicConfig(level=logging.WARNING)


# create dirs
for d in "../data/preprocessed", "../data/extracted":
    if not os.path.exists(d):
        os.mkdir(d)


def load_session_csv(path: str) -> pd.DataFrame:
    """load the data from a csv that contains a db dump
    csv has "comment" columns that start with '#'
    after each comment block ( 3 lines usually), the headers of the columns are
    newly specified

    this function will
    1. load the data
    2. pivot with time
    3. compute laps

    :param path: path to the csv file
    :return: pd.Dataframe
    """

    # load the file a
    with open(path) as fh:
        txt = fh.read()

    # split into dumps
    # this marks the start of a new dataset/dataset
    start_str = "#group"
    dataset_txts = [start_str + dataset_txt for dataset_txt in txt.split(start_str)[1:]]

    # load each as dataframe and combine
    dfs = [
        pd.read_csv(StringIO(dataset_txt), comment="#") for dataset_txt in dataset_txts
    ]
    df = pd.concat(dfs)

    # make sure this only 1 session
    assert len(df["_start"].unique()) == 1
    assert len(df["SessionId"].unique()) == 1

    # transform to time index with 1 feature per column
    df = df.pivot("_time", "_field", "_value")

    # fill missing values
    fill_cols = ["Throttle", "Brake", "TrackPositionPercent", "SteeringAngle", "Gear"]
    df.loc[:, fill_cols] = df.loc[:, fill_cols].fillna(method="ffill")

    # compute laps
    df["new_lap_start"] = df["TrackPositionPercent"].diff() < -0.9
    df["lap"] = df["new_lap_start"].cumsum()
    return df


def compute_spatial_trajectory(lap_df, interpolation_step_size=0.001, segments=100):
    """
    convert from time index to space index
    use lap_df (that has time index), take the track position as new index and interpolate to linear grid
    :return: new dataframe with interpolated values
    """
    assert len(lap_df["lap"].unique()) == 1

    x = np.arange(0, 1, interpolation_step_size)
    brake = np.interp(x, lap_df["TrackPositionPercent"], lap_df["Brake"])
    steering_angle = np.interp(
        x, lap_df["TrackPositionPercent"], lap_df["SteeringAngle"]
    )
    throttle = np.interp(x, lap_df["TrackPositionPercent"], lap_df["Throttle"])

    # speed = np.interp(x, lap_df["TrackPositionPercent"], lap_df["SpeedKmh"])

    df = pd.DataFrame(
        {
            "x": x,
            "brake": brake,
            "steering_angle": steering_angle,
            "throttle": throttle,
            # "speed": speed,
        }
    )

    df["segment"] = (df["x"] * segments).astype(int)
    df = df.groupby("segment").mean().drop("x", axis=1)

    return df


def extract_laps_from_session_csv(inpath: str, out_dir="../data/extracted/"):
    """call the lower level functions to load the session data,
    then interpolate lap data
    and store lap data in individual csv files
    """
    session_df = load_session_csv(inpath)
    for lap in session_df["lap"].dropna().unique():
        fname = f"{inpath.split('/')[-1][:-4]}-lap{lap}.csv"
        outpath = os.path.join(out_dir, fname)
        session_df[session_df["lap"] == lap].to_csv(outpath)
        log.info(f"wrote file: {outpath}")


def preprocess_lap(inpath: str, outpath: str):
    """pass"""
    df = pd.read_csv(inpath)
    df = compute_spatial_trajectory(df)
    df.to_csv(outpath)
    log.info(f"wrote file: {outpath}")


if __name__ == "__main__":
    path = "../data/raw/89db51de-22a6-4033-8201-2fc37a5fe905.csv"
    extract_laps_from_session_csv(path)

    for inpath in pathlib.Path().glob("../data/extracted/*lap*.csv"):
        outpath = f"../data/preprocessed/{inpath.name}"
        preprocess_lap(inpath, outpath)
