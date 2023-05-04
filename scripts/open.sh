#!/usr/bin/env bash

set -x
cd "$(dirname "$0")"

# exit on failure
# set -e

oc project b4mad-racing

case $1 in
  telemetry)
    # URL=$(oc get routes/telemetry --template='{{ .spec.port.targetPort }}://{{ .spec.host }}')
    URL=$(oc get routes/telemetry --template='https://{{ .spec.host }}')
    ;;
  grafana)
    URL=$(oc get routes/grafana --template='https://{{ .spec.host }}')
    ;;
  paddock)
    URL=$(oc get routes/paddock --template='https://{{ .spec.host }}')
    oc extract secret/paddock-settings --to=- --keys=DJANGO_SUPERUSER_PASSWORD --keys=DJANGO_SUPERUSER_USERNAME
    ;;
  *)
    echo "Usage: $0 [telemetry|grafana]"
    exit 1
    ;;
esac

open $URL
