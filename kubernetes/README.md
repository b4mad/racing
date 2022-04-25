# README

```shell
# one time for helm configuration
helm repo add influxdata https://helm.influxdata.com/
helm repo add bitnami https://charts.bitnami.com/bitnami

# bring up the cluster
kind create cluster --config=dev-cluster.yaml
# and an ingress...
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# deploy influx and telegraf
helm upgrade --install b4mad-racing-influxdb2 bitnami/influxdb \
  --namespace b4mad-racing --values influxdb2-values.yaml \
  --create-namespace

echo $(kubectl get secret b4mad-racing-influxdb2-auth -o "jsonpath={.data['admin-password']}" --namespace b4mad-racing | base64 --decode)

```

`mosquitto_pub -u admin -P admin -t racing -p 443 -h mosquitto-ephemeral-tls-b4mad-racing.apps.smaug.na.operate-first.cloud --cafile mosquitto_ca.crt --insecure -i test -d -m '{"time":1649437794,"vehicleInformation":{"mCarName":"Ford Focus RS","mCarClassName":"Road C2"},"carState":{"mSpeed":62,"mRpm":5.6978,"mBrake":7050,"mThrottle":0,"mClutch":0,"mSteering":0,"mGear":1},"motionAndDeviceRelated":{"mOrientation":[0,-0.0129591,-1.56414]}}'`
