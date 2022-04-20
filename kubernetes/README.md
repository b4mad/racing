# README

```shell
# one time for helm configuration
helm repo add influxdata https://helm.influxdata.com/

# bring up the cluster
kind create cluster --config=dev-cluster.yaml
# and an ingress...
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# deploy influx and telegraf
helm upgrade --install b4r-test-influxdb2 influxdata/influxdb2 \
  --namespace b4r-test --values influxdb2-values.yaml \
  --create-namespace
helm upgrade --install b4r-test-telegraf influxdata/telegraf \
  --namespace b4r-test --values telegraf-values.yaml
helm upgrade --install b4r-test-mosquitto t3n/mosquitto \
  --namespace b4r-test --values mosquitto-values.yaml                    

kubectl apply -f influxdb2-ingress.yaml 

echo $(kubectl get secret b4r-test-influxdb2-auth -o "jsonpath={.data['admin-password']}" --namespace b4r-test | base64 --decode)

```
