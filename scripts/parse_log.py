#!/usr/bin/env python3

import csv
import re
import sys

# import os
# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(parent_dir)
# # from components.paddock.telemetry.models import Coach
# from components.paddock.telemetry.pitcrew.message import Message


# One commonly used average reading speed for English is around 150 words per minute
# when spoken. This translates to 2.5 words per second. So you can estimate the time
# it takes to read a phrase out loud by counting the words and dividing by 2.5.
# or check https://github.com/alanhamlett/readtime
def read_time(msg=""):
    words = len(msg.split(" "))
    # r_time = words / 1.5
    r_time = words / 2.2
    delta_add = 2.0
    delta_add = 0.2
    # self.log_debug(f"read_time: '{msg}' ({words}) {r_time:.1f} seconds + {delta_add:.1f} seconds")
    # return words * 0.8  # avg ms per word
    # return words / 2.5  # avg ms per word
    return r_time + delta_add


def sorted_lines(lines):
    lines_dicts = []
    for line in lines:
        line_dict = {"line": line, "sort_key": 0.0}
        # use pattern matching to extract stat_total_duration
        # m = re.match(r'.*stat_total_duration=(\d+\.\d+)ms.*', line)
        m = re.match(r".*status_code=(\d+) .*", line)
        if m:
            duration = float(m.group(1))
            # print(f'Duration: {duration}')
            line_dict["sort_key"] = duration

        lines_dicts.append(line_dict)

    # now sort lines by sort_key
    sorted_lines = sorted(lines_dicts, key=lambda line: line["sort_key"])

    for line in sorted_lines:
        print("%s: %s" % (line["sort_key"], line["line"].strip()))
        # print(line['line'].strip())


def find_event(data, msg, is_none="play"):
    for i in range(len(data) - 1, -1, -1):
        if data[i]["msg"] == msg:
            if data[i].get(is_none) is None:
                return data[i]
            else:
                sys.stderr.write(f"Warning: {msg} already has {is_none} set to {data[i][is_none]}\n")
                return {}
    return {}


def extract_cc_data(lines):
    data = []
    for line in lines:
        # 19:27:57.502 : MQTT: queue mqtt_response_brake hard gear 3_0 - drt: 4141.392
        m = re.match(r".*queue mqtt_response_([\w _]+) - drt: (\d+\.\d+).*", line)
        if m:
            event = {}
            msg = m.group(1)
            drt = m.group(2)
            txt, distance = msg.split("_")
            event["msg"] = msg
            event["read_time"] = round(read_time(txt), 2)
            event["queue"] = drt
            event["distance"] = distance
            data.append(event)
            continue
        # 19:29:17.923 : MQTT: play mqtt_response_brake hard gear 4_2842 -  max: 2857 drt: 2842.955
        m = re.match(r".*play mqtt_response_([\w _]+) -  max: (\d+) drt: (\d+\.\d+).*", line)
        if m:
            msg = m.group(1)
            max_distance = m.group(2)
            drt = m.group(3)
            event = find_event(data, msg, is_none="max_distance")
            event["max_distance"] = max_distance
            continue
        # 19:29:19.442 : MQTT - AudioPlayer - COMPOUND_mqtt_response_brake hard gear 4_2842 finished drt: 2945.812 time: 1.5190201 # noqa: E501
        m = re.match(r".*COMPOUND_mqtt_response_([\w _]+) finished drt: (\d+\.\d+) time: (\d+\.\d+).*", line)
        if m:
            msg = m.group(1)
            drt = m.group(2)
            play_time = m.group(3)
            event = find_event(data, msg, is_none="play_time")
            event["play_time"] = play_time
            if event.get("read_time") is not None:
                event["read_delta"] = round(float(play_time) - event["read_time"], 2)
            event["finished"] = drt
            continue
        # 19:36:27.757 : MQTT - AudioPlayer - COMPOUND_mqtt_response_brake 9_3809 drt: 3810.264
        m = re.match(r".*COMPOUND_mqtt_response_([\w _]+) drt: (\d+\.\d+).*", line)
        if m:
            msg = m.group(1)
            drt = m.group(2)
            event = find_event(data, msg, is_none="play")
            if event.get("distance") is not None:
                event["play_delta"] = round(float(drt) - float(event["distance"]), 2)
            event["play"] = drt
            continue
        # 19:29:48.669 : Clip COMPOUND_mqtt_response_brake 9_3809 has expired after being queued for 10032 milliseconds
        m = re.match(
            r".*Clip COMPOUND_mqtt_response_([\w _]+) has expired after being queued for (\d+) milliseconds.*", line
        )
        if m:
            msg = m.group(1)
            queue_time = m.group(2)
            event = find_event(data, msg)
            event = find_event(data, msg, is_none="play")
            event["not_played_reason"] = "expired"
            event["expired"] = queue_time
            continue
        # 19:30:34.125 : Clip COMPOUND_mqtt_response_brake 5_1536will not be played because higher priority message is waiting to be played: penalties/cut_track_race_1  # noqa: E501
        m = re.match(
            r".*Clip COMPOUND_mqtt_response_([\w _]+)will not be played because higher priority message is waiting to be played: ([\w _]+).*",  # noqa: E501
            line,
        )
        if m:
            msg = m.group(1)
            higher_priority_msg = m.group(2)
            event = find_event(data, msg)
            event = find_event(data, msg, is_none="play")
            event["not_played_reason"] = "higher_priority_msg"
            event["higher_priority_msg"] = higher_priority_msg
            continue

    # for event in data:
    #     print(event)

    # convert data to a csv using csv module
    # print csv lines to stdout

    # print header
    fieldnames = [
        "msg",
        "queue",
        "distance",
        "play",
        "play_delta",
        "finished",
        "max_distance",
        "play_time",
        "read_time",
        "read_delta",
        "not_played_reason",
        "expired",
        "higher_priority_msg",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for event in data:
        writer.writerow(event)


lines = sys.stdin.readlines()
# sorted_lines(lines)
extract_cc_data(lines)
