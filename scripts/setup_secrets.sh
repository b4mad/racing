#!/usr/bin/env bash
set -x

# exit on failure
# set -e

oc project b4mad-racing

# INFLUX_URL=$(oc get routes/telemetry --template='{{ .spec.port.targetPort }}://{{ .spec.host }}')
INFLUX_URL=https://telemetry.b4mad.racing
INFLUXDB_ADMIN_TOKEN=$(oc get secrets -n b4mad-racing influxdb2-auth -o go-template='{{index .data "admin-user-token"}}' | base64 -d)
CONFIG=b4mad-racing-$$

influx config create \
    -n $CONFIG \
    -u $INFLUX_URL \
    -t "$INFLUXDB_ADMIN_TOKEN" \
    -o b4mad

# Get org id
ORG_ID=$(influx org list -c $CONFIG --json | jq -r '.[] | select(.name == "b4mad") | .id')

# Get bucket ids
FAST_BUCKET_ID=$(influx bucket list -c $CONFIG --json | jq -r --arg orgid "$ORG_ID" '.[] | select(.name == "fast_laps" and .orgID == $orgid) | .id')
RACING_BUCKET_ID=$(influx bucket list -c $CONFIG --json | jq -r --arg orgid "$ORG_ID" '.[] | select(.name == "racing" and .orgID == $orgid) | .id')

# # Get Grafana token
# GRAFANA_TOKEN=$(influx auth list -c $CONFIG --json | jq -r --arg fast_id "$FAST_BUCKET_ID" --arg racing_id "$RACING_BUCKET_ID" '.[] | select(.permissions[] | contains($fast_id) and contains($racing_id)) | .token')
# GRAFANA_TOKEN=$(influx auth list -c $CONFIG --json | jq -r --arg fast_id "$FAST_BUCKET_ID" --arg racing_id "$RACING_BUCKET_ID" --arg org_id "$ORG_ID" '.[] | select(.permissions[] | contains("read:orgs/\($org_id)/buckets/\($fast_id)")) | .token')
# GRAFANA_TOKEN=$(influx auth list -c $CONFIG --json | jq -r --arg fast_id "$FAST_BUCKET_ID" --arg racing_id "$RACING_BUCKET_ID" --arg org_id "$ORG_ID" '.[] | select(.permissions[] | contains("read:orgs/\($org_id)/buckets/\($fast_id)") or contains("read:orgs/\($org_id)/buckets/\($racing_id)")) | .token')


# if [[ -z "$GRAFANA_TOKEN" ]]; then
#     GRAFANA_TOKEN=$(influx auth create -c $CONFIG -o "$ORG_ID" -d grafana_reader --read-bucket "$FAST_BUCKET_ID" --read-bucket "$RACING_BUCKET_ID" --json | jq -r '.token')
# fi


# # Get Telegraf token
# TELEGRAF_TOKEN=$(influx auth list -c $CONFIG --json | jq -r --arg bucketid "$RACING_BUCKET_ID" '.[] | select(.description == "telegraf_writer" and (.permissions[] | select(. == "write:$bucketid")) != null) | .token')
# if [ -z "$TELEGRAF_TOKEN" ]; then
#     TELEGRAF_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d telegraf_writer --write-bucket $RACING_BUCKET_ID --json | jq -r '.token')
# fi

# Create new tokens if they don't exist
# if [[ -z "$GRAFANA_TOKEN" ]]; then
#   GRAFANA_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d grafana_reader --read-bucket $FAST_BUCKET_ID --read-bucket $RACING_BUCKET_ID --json | jq -r '.token')
# fi

# if [[ -z "$TELEGRAF_TOKEN" ]]; then
#   TELEGRAF_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d telegraf_writer --write-bucket $RACING_BUCKET_ID --json | jq -r '.token')
# fi


GRAFANA_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d grafana_reader --read-bucket $FAST_BUCKET_ID --read-bucket $RACING_BUCKET_ID  --json | jq -r '.token')
TELEGRAF_TOKEN=$(influx auth create -c $CONFIG -o b4mad -d telegraf_writer --write-bucket $RACING_BUCKET_ID --json | jq -r '.token')

# update the secret
# oc create secret generic -n b4mad-racing influx-grafana-auth --from-literal=GRAFANA_READER_TOKEN=$TOKEN
oc patch secret influx-grafana-auth --type='json' -p='[{"op": "replace", "path": "/data/GRAFANA_READER_TOKEN", "value": "'$(echo -n "$GRAFANA_TOKEN" | base64)'" }]'
oc create secret generic influx-telegraf --from-literal=token=$TELEGRAF_TOKEN || \
oc patch secret influx-telegraf --type='json' -p='[{"op": "replace", "path": "/data/token", "value": "'$(echo -n "$TELEGRAF_TOKEN" | base64)'" }]'

# patch the datasource to trigger an update
oc patch GrafanaDatasource racing --type=json -p='[{"op": "replace", "path": "/spec/datasource/editable", "value": false}]'

influx config rm $CONFIG
