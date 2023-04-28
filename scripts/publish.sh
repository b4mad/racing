#!/usr/bin/env sh

set -x
cd "$(dirname "$0")"

T='{"CarModel": "Ferrari 488 GT3 Evo 2020",    "GameName": "iRacing",   "SessionId": "1669233672",    "SessionTypeName": "Race",    "TrackCode": "sebring international",    "Brake": 0.0,    "Clutch": 1.0,    "CurrentLap": 1.0,    "CurrentLapTime": 0.0,    "DistanceRoundTrack": 5564.84961,    "Gear": 3.0,    "Handbrake": 0.0,    "Rpms": 0.0,    "SpeedMs": 46.2075653,    "SteeringAngle": -0.232568219,    "Throttle": 0.995530248}'

if [ -z "$MQTT_HOST" ]; then
  MQTT_HOST=telemetry.b4mad.racing
fi
CLIENT_ID=$(hostname)-$$

mosquitto_pub -u crewchief -P crewchief \
  -t "replay/crewchief/durandom/1669233999/iRacing/sebring international/Ferrari 488 GT3 Evo 2021/Race" \
  -p 31883 -h $MQTT_HOST -i $CLIENT_ID -d \
  -m "`cat sample.json`"
