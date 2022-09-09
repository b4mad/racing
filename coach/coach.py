#!/usr/bin/python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import json

brakepoints = [460, 1680, 2200, 3520, 4750, 5100]
previous_response = 0

def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))


def on_message(mqttc, obj, msg):
    global previous_response
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    telemetry = json.loads(msg.payload.decode('utf-8'))
    # print(telemetry['time'])
    # print(telemetry['telemetry']['Brake'])

    m = telemetry['telemetry']['DistanceRoundTrack']
    for(i, bp) in enumerate(brakepoints):
        if m < bp:
            distance_to_brakepoint = bp - m
            if distance_to_brakepoint < 5:
                response = 1
                if response != previous_response:
                    print(f"Brake now {m - bp}")
                    mqttc.publish("racing/response/durandom", response)
                    previous_response = response
                    break
            elif distance_to_brakepoint < 50:
                response = 50
                if response != previous_response:
                    print(f"Brake now {m - bp}")
                    mqttc.publish("racing/response/durandom", response)
                    previous_response = response
                    break
            elif distance_to_brakepoint < 100:
                response = 100
                if response != previous_response:
                    print(f"Brake now {m - bp}")
                    mqttc.publish("racing/response/durandom", response)
                    previous_response = response
                    break



def on_publish(mqttc, obj, mid):
    print("mid: " + str(mid))


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc, obj, level, string):
    print(string)


mqttc = mqtt.Client()
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
mqttc.on_log = on_log
mqttc.username_pw_set('admin', 'admin')
mqttc.connect("telemetry.b4mad.racing", 31883, 60)
mqttc.subscribe("crewchief/durandom/#", 0)

mqttc.loop_forever()
