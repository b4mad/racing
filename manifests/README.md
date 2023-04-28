# Deploy Telemetry infrastructure

the structure of this folder is inspired by https://github.com/kostis-codefresh/gitops-environment-promotion


## deploy Influxdb2

via helm:

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm upgrade --install influxdb2 bitnami/influxdb \
  --namespace b4mad-racing \
  --values influxdb2-values.yaml
```

## deploy Telegraf and Mosquitto

this is via `kustomize build --enable_alpha_plugins . | oc apply -f -`
Keep in mind to have the SOPS plugin installed.
