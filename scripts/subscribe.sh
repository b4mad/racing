#!/usr/bin/env sh

set -x
cd "$(dirname "$0")"

if [ -z "$MQTT_HOST" ]; then
  MQTT_HOST=telemetry.b4mad.racing
fi
CLIENT_ID=$(hostname)-$$

if [ ! -z "$DRIVER" ]; then
  DRIVER="${DRIVER}/"
fi

if [ -z "$MQTT_TOPIC" ]; then
  MQTT_TOPIC="crewchief/${DRIVER}#"
fi

mosquitto_sub -u crewchief -P crewchief \
  -t $MQTT_TOPIC \
  -p 31883 -h $MQTT_HOST -i $CLIENT_ID -d
