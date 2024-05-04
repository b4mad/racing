#!/usr/bin/env bash
set -x
PG_CLUSTER_USER_SECRET_NAME=paddock-app
# HOST=$(kubectl get ingress/influx --template='{{ .spec.host }}')
HOST=telemetry.b4mad.racing

oc project b4mad-racing-test

PGPASSWORD=$(kubectl get secrets "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.password | base64decode}}') \
PGUSER=$(kubectl get secrets "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.user | base64decode}}') \
PGDATABASE=$(kubectl get secrets "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.dbname | base64decode}}') \
/opt/homebrew/bin/psql -h $HOST -p 31432
