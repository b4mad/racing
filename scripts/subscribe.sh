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

# default to secure connection
if [ -z "$SKIP_TLS" ]; then
  MQTT_PORT=30883
  TLS_CERT_OPTS="--tls-use-os-certs"
else
  MQTT_PORT=31883
  TLS_CERT_OPTS=""
fi

mosquitto_sub -u crewchief -P crewchief \
  -p $MQTT_PORT -h $MQTT_HOST $TLS_CERT_OPTS \
  -i $CLIENT_ID -d \
  -t $MQTT_TOPIC
