#!/usr/bin/env bash
set -x

# exit on failure
# set -e

oc project b4mad-racing

INFLUX_URL=$(oc get routes/telemetry --template='{{ .spec.port.targetPort }}://{{ .spec.host }}')
INFLUXDB_ADMIN_TOKEN=$(oc get secrets -n b4mad-racing influxdb2-auth -o go-template='{{index .data "admin-user-token"}}' | base64 -d)
CONFIG=b4mad-racing-$$

influx config create \
    -n $CONFIG \
    -u $INFLUX_URL \
    -t "$INFLUXDB_ADMIN_TOKEN" \
    -o b4mad

# influx bucket delete -c $CONFIG -n fast_laps -o b4mad
influx bucket create -c $CONFIG -n fast_laps -r 0 -d "Bucket for fast lap telemetry"

influx config rm $CONFIG
