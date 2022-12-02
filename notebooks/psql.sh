#!/usr/bin/env bash

PG_CLUSTER_USER_SECRET_NAME=b4mad-racing-pguser-free-practice
PG_CLUSTER_USER_SECRET_NAME=b4mad-racing-pguser-paddock

PGPASSWORD=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.password | base64decode}}') \
PGUSER=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.user | base64decode}}') \
PGDATABASE=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.dbname | base64decode}}') \
/opt/homebrew/Cellar/libpq/15.0/bin/psql -h telemetry.b4mad.racing -p 31884
