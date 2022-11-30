#!/usr/bin/env sh

set -x
cd "$(dirname "$0")"

T='{"CarModel": "Ferrari 488 GT3 Evo 2020",    "GameName": "iRacing",   "SessionId": "1669233672",    "SessionTypeName": "Race",    "TrackCode": "sebring international",    "Brake": 0.0,    "Clutch": 1.0,    "CurrentLap": 1.0,    "CurrentLapTime": 0.0,    "DistanceRoundTrack": 5564.84961,    "Gear": 3.0,    "Handbrake": 0.0,    "Rpms": 0.0,    "SpeedMs": 46.2075653,    "SteeringAngle": -0.232568219,    "Throttle": 0.995530248}'

mosquitto_pub -u crewchief -P crewchief \
  -t "crewchief/durandom/1669233999/iRacing/sebring international/Ferrari 488 GT3 Evo 2021/Race" \
  -p 31883 -h telemetry.b4mad.racing -i test -d \
  -m "`cat sample.json`"
