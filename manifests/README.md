# Deploy Telemetry infrastructure

## deploy Influxdb2

via helm: `helm upgrade --install b4mad-racing-influxdb2 bitnami/influxdb --namespace b4mad-racing --values influxdb2-values.yaml`

## deploy Telegraf and Mosquitto

this is via `kustomize build . | oc apply -f -`
