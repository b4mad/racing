#!/usr/bin/env bash

set -x

PG_CLUSTER_USER_SECRET_NAME=postgresql-app

DATE=2024-05-03_19-34-52

PGPASSWORD=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.password | base64decode}}') \
PGUSER=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.user | base64decode}}') \
PGDATABASE=$(kubectl get secrets -n b4mad-racing "${PG_CLUSTER_USER_SECRET_NAME}" -o go-template='{{.data.dbname | base64decode}}') \
PORT=30432
pg_restore -h telemetry.b4mad.racing -p ${PORT} -U $PGUSER -d $PGDATABASE data/backup_paddock-${DATE}.tar

# pg_dump -h telemetry.b4mad.racing -p 31884 -F t -f data/backup_paddock.tar
# pg_dumpall -U $PGUSER -h telemetry.b4mad.racing -p 31884 -f data/backup_paddock.sql
# postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
# pg_dumpall --dbname=postgresql://${PGUSER} -f data/backup_paddock.sql
