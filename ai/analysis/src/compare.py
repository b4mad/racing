#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" compare 2 laps """
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

expert_path = "../data/preprocessed/89db51de-22a6-4033-8201-2fc37a5fe905-lap11.csv"
student_path = "../data/preprocessed/89db51de-22a6-4033-8201-2fc37a5fe905-lap13.csv"


def normalize(df):
    """
    normalize
    throttle is mostly 0 or 100, anything in between is possible
    brake is mostly 0 or 100, anything in between is possible
    steering_angle is somewhat normally distributed around 0 / or a given offset

    """
    df["throttle"] /= 100
    df["brake"] /= 100
    df["steering_angle"] /= 100
    return df


def compute_metric(expert_df: pd.DataFrame, student_df: pd.DataFrame):
    """
    compute distance metric for each segment
    """

    # compute normalized difference
    diff_df = student_df - expert_df

    # compute metric
    metric_df = pd.DataFrame((diff_df**2).sum(1))
    metric_df.columns = ["metric"]
    return metric_df


def compute_suggestions(expert_df, student_df):
    """
    compute suggestion for each segment:
    take feature with biggest difference
    and create a list of suggestions
    """
    # get feature wise distances
    diff_df = student_df - expert_df

    # compute feature with the greatest distance
    selected_features = diff_df.abs().values.argmax(1)

    # get direction of error
    signs = [
        sign[feature]
        for sign, feature in zip(np.sign(diff_df.values), selected_features)
    ]

    feature_names = diff_df.columns
    suggestions = [
        f"{feature_names[feature]} is too {'high' if sign > 0 else 'low'}"
        for feature, sign in zip(selected_features, signs)
    ]

    return pd.DataFrame({"suggestion": suggestions}, index=diff_df.index)
    selected_features = [np.array(diff_df.columns)[selected_features]]

    fig, ax = plt.subplots(2, len(diff_df.columns) - 1, sharex=True, sharey=True)
    for i, c in enumerate(diff_df.columns[1:]):
        student_df[c].plot(ax=ax[0, i])
        expert_df[c].plot(ax=ax[0, i])
        diff_df[c].plot(ax=ax[1, i])
        diff_df[c].rolling(10).mean().plot(ax=ax[1, i])
        ax[0, i].set_title(c)
        ax[1, i].set_title(c + " diff")
    plt.tight_layout()
    plt.show()

    # improvment possibilities

    plot()
    plt.show()


def rank_suggestions(metrics, suggestions, n):
    """return list of n suggestions"""
    df = pd.concat([metrics, suggestions], axis=1)
    df.sort_values("metric", ascending=False, inplace=True)
    return df[:n]


def analyse_csv(expert_path, student_path, n_suggestions):
    """
    analyse the preprocessed laps, comparing student and expert and make suggestions
    """

    # load data
    expert_df = pd.read_csv(expert_path).set_index("segment")
    student_df = pd.read_csv(student_path).set_index("segment")

    # normalize
    expert_df = normalize(expert_df)
    student_df = normalize(student_df)

    # compute metrics
    metrics = compute_metric(expert_df, student_df)

    # compute suggestions
    suggestions = compute_suggestions(expert_df, student_df)

    # get top suggestions
    ranked_suggestions = rank_suggestions(metrics, suggestions, n=n_suggestions)

    # convert to list of suggestions
    return ranked_suggestions.reset_index().to_dict("records")


if __name__ == "__main__":

    expert_path = "../data/preprocessed/89db51de-22a6-4033-8201-2fc37a5fe905-lap11.csv"
    student_path = "../data/preprocessed/89db51de-22a6-4033-8201-2fc37a5fe905-lap13.csv"
    n_suggestions = 10

    suggestions = analyse_csv(expert_path, student_path, n_suggestions)
    print(suggestions)
