#!/usr/bin/env sh

set -x
cd "$(dirname "$0")"

if [ -z "$MQTT_HOST" ]; then
  MQTT_HOST=telemetry.b4mad.racing
fi
CLIENT_ID=$(hostname)-$$


mosquitto_sub -u crewchief -P crewchief \
  -t "/crewchief/#" \
  -p 31883 -h $MQTT_HOST -i $CLIENT_ID -d
