#!/usr/bin/env bash

set -x

PG_CLUSTER_USER_SECRET_NAME=b4mad-racing-pguser-free-practice
PG_CLUSTER_USER_SECRET_NAME=b4mad-racing-pguser-paddock
PG_CLUSTER_USER_SECRET_NAME=b4mad-racing-pguser-paddock-root

DATE=$(date +%Y-%m-%d_%H-%M-%S)

PGPASSWORD=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.password | base64decode}}') \
PGUSER=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.user | base64decode}}') \
PGDATABASE=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.dbname | base64decode}}') \
pg_dumpall -h telemetry.b4mad.racing -p 31884 -f data/backup_paddock-${DATE}.sql

# pg_dump -h telemetry.b4mad.racing -p 31884 -F t -f data/backup_paddock.tar
# pg_dumpall -U $PGUSER -h telemetry.b4mad.racing -p 31884 -f data/backup_paddock.sql
# postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
# pg_dumpall --dbname=postgresql://${PGUSER} -f data/backup_paddock.sql
