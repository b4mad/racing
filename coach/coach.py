#!/usr/bin/env python3

import os
import json
import csv
import logging

import paho.mqtt.client as mqtt


logging.basicConfig(level=logging.DEBUG)


brakepoints = []
previous_response = 0
brakepoint_idx = 0
previous_brakepoint_idx = len(brakepoints) - 1
track_length = 3600

CREWCHIEF_USERNAME = os.environ.get("CREWCHIEF_USERNAME", "durandom")
B4MAD_RACING_CLIENT_USER = os.environ.get("B4MAD_RACING_CLIENT_USER", "crewchief")
B4MAD_RACING_CLIENT_PASSWORD = os.environ.get(
    "B4MAD_RACING_CLIENT_PASSWORD", "crewchief"
)
B4MAD_RACING_BRAKEPOINT_FILENAME = os.getcwd() + "/brakepoints.csv"


def get_brakepoint(meters):
    global brakepoint_idx, previous_brakepoint_idx
    brakepoint = brakepoints[brakepoint_idx]
    previous_brakepoint = brakepoints[previous_brakepoint_idx]

    if previous_brakepoint_idx < brakepoint_idx:
        if meters >= previous_brakepoint["stop"] and meters < brakepoint["stop"]:
            return brakepoint
    else:
        if meters >= previous_brakepoint["stop"] or meters < brakepoint["stop"]:
            return brakepoint

    previous_brakepoint_idx = brakepoint_idx
    brakepoint_idx += 1
    if brakepoint_idx >= len(brakepoints):
        brakepoint_idx = 0
    return get_brakepoint(meters)


def get_response(meters):
    global previous_response
    brakepoint = get_brakepoint(meters)
    distance_to_brakepoint = brakepoint["start"] - meters
    if distance_to_brakepoint > 0 and distance_to_brakepoint < 200:
        if distance_to_brakepoint > 150:
            response = brakepoint["gear"]
        elif distance_to_brakepoint > 50:
            response = brakepoint["break_force"]
        else:
            response = 50

        if response != previous_response:
            previous_response = response
            return response
    else:
        distance_to_brakepoint_stop = brakepoint["stop"] - meters
        if distance_to_brakepoint_stop > 0 and distance_to_brakepoint_stop < 10:
            response = 10
            if response != previous_response:
                previous_response = response
                return response
    return None


def load_breakpoint() -> None:
    """Load the brakepoints from the csv file"""
    logging.debug("loading brakepoints from %s", B4MAD_RACING_BRAKEPOINT_FILENAME)

    with open(B4MAD_RACING_BRAKEPOINT_FILENAME, mode="r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            brakepoint = {}
            for key in row:
                brakepoint[key] = int(row[key])
            brakepoints.append(brakepoint)

    logging.debug("loaded %s brakepoints", len(brakepoints))


def on_message(mqttc, obj, msg):
    """Handle incoming messages, we are only interested in the telemetry.

    Args:
        mqttc (_type_): the mqtt client
        obj (_type_): the userdata
        msg (_type_): the message received
    """
    logging.debug(
        "%s: qos='%s',payload='%s'", msg.topic, str(msg.qos), str(msg.payload)
    )

    telemetry = json.loads(msg.payload.decode("utf-8"))

    meters = telemetry["telemetry"]["DistanceRoundTrack"]
    response = get_response(meters)
    if response:
        logging.debug("meters: %s, response: %s", meters, response)
        mqttc.publish(f"/coach/{CREWCHIEF_USERNAME}", response)


def on_connect(mqttc, obj, flags, rc):
    logging.debug("rc: %s", str(rc))


def on_publish(mqttc, obj, mid):
    logging.debug("mid: %s", str(mid))


def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.debug("subscribed: mid='%s', granted_qos='%s'", str(mid), str(granted_qos))


# def on_log(mqttc, obj, level, string):
#     print(string)

if __name__ == "__main__":
    test = True
    test = False

    load_breakpoint()

    if test:
        for j in range(1, 4):
            logging.info("lap %s", j)
            for i in range(0, 3500):
                response = get_response(i)
                if response:
                    logging.info("meters: %s, response: %s", i, response)
    else:
        mqttc = mqtt.Client()
        mqttc.on_message = on_message
        mqttc.on_connect = on_connect
        mqttc.on_publish = on_publish
        mqttc.on_subscribe = on_subscribe
        # mqttc.on_log = on_log
        mqttc.username_pw_set(B4MAD_RACING_CLIENT_USER, B4MAD_RACING_CLIENT_PASSWORD)
        mqttc.connect("telemetry.b4mad.racing", 31883, 60)
        mqttc.subscribe(f"crewchief/{CREWCHIEF_USERNAME}/#", 0)
        mqttc.loop_forever()
