# Deploy Telemetry infrastructure

## deploy Influxdb2

via helm:

```shell
helm upgrade --install influxdb2 bitnami/influxdb \
  --namespace b4mad-racing \
  --values influxdb2-values.yaml
```

## deploy Telegraf and Mosquitto

this is via `kustomize build --enable_alpha_plugins . | oc apply -f -`
Keep in mind to have the SOPS plugin installed.
