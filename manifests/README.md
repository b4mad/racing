# Deploy Telemetry infrastructure

the structure of this folder is inspired by <https://github.com/kostis-codefresh/gitops-environment-promotion>

## Deploying to a new OpenShift cluster

```shell
kustomize build --enable-alpha-plugins manifests/env/phobos | oc apply -f -
sleep 60
scripts/setup_buckets.sh
scripts/setup_secrets.sh
scripts/setup_trigger_updates.sh
scripts/open.sh paddock
scripts/open.sh telemetry
scripts/open.sh grafana
```

## Continuous Deployment via ArgoCD

`racing.yaml` contains an ArgoCD Application that could be used with Operate First Argocd depoloyed at nostromo.
