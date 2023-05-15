helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm template influxdb2 bitnami/influxdb \
  --values influxdb2-values.yaml \
  --output-dir influxdb2

the helm chart is at https://github.com/bitnami/charts/tree/main/bitnami/influxdb/
# run the init script

```
oc delete job/influxdb-init && oc create -f init.yaml &&  sleep 1 && oc logs -f job/influxdb-init -c influxdb-init
```

^^ deprecated by: ../../../scripts/setup_buckets.sh
