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

FAST_BUCKET_ID=$(influx bucket list -c $CONFIG --json | jq -r '.[] | select(.name == "fast_laps") | .id')
RACING_BUCKET_ID=$(influx bucket list -c $CONFIG --json | jq -r '.[] | select(.name == "racing") | .id')

GRAFANA_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d grafana_reader --read-bucket $FAST_BUCKET_ID --read-bucket $RACING_BUCKET_ID  --json | jq -r '.token')
TELEGRAF_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d telegraf_writer --write-bucket $RACING_BUCKET_ID --json | jq -r '.token')

# update the secret
# oc create secret generic -n b4mad-racing influx-grafana-auth --from-literal=GRAFANA_READER_TOKEN=$TOKEN
oc patch secret influx-grafana-auth --type='json' -p='[{"op": "replace", "path": "/data/GRAFANA_READER_TOKEN", "value": "'$(echo -n "$GRAFANA_TOKEN" | base64)'" }]'
oc patch secret telegraf --type='json' -p='[{"op": "replace", "path": "/data/influx-token", "value": "'$(echo -n "$TELEGRAF_TOKEN" | base64)'" }]'

# patch the datasource to trigger an update
oc patch GrafanaDatasource racing --type=json -p='[{"op": "replace", "path": "/spec/datasource/editable", "value": false}]'

influx config rm $CONFIG
