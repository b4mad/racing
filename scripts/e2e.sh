#!/usr/bin/env bash
set -x
cd "$(dirname "$0")"

# exit on failure
# set -e

oc project b4mad-racing

MQTT_HOST=$(oc get routes/telemetry --template='{{ .spec.host }}')
MQTT_PORT=$(oc get service/mosquitto-tcp -o jsonpath='{.spec.ports[0].nodePort}')
CLIENT_ID=$(hostname)-$$

mosquitto_pub -u crewchief -P crewchief \
  -t "crewchief/durandom/1669233999/iRacing/sebring international/Ferrari 488 GT3 Evo 2021/Race" \
  -p $MQTT_PORT -h $MQTT_HOST -i $CLIENT_ID -d \
  -m "`cat sample.json`"
