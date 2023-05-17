# Deploy Telemetry infrastructure

the structure of this folder is inspired by <https://github.com/kostis-codefresh/gitops-environment-promotion>

## creating secrets

This `env/phobos-test` we are introducing [sealed secrets](https://sealed-secrets.netlify.app/). Assuming that you have
an `.env` file containing the current set of secrets you want to use, and assuming you are logged in the `phobos`
cluster, the following command will generate the resource file:

```shell
kubectl --namespace b4mad-racing-test --dry-run=client \
    create secret generic paddock-settings \
    --from-env-file .env \
    --output yaml \
| kubeseal --controller-namespace=sealed-secrets \
    --format yaml \
> manifests/env/phobos-test/paddock-settings.yaml
```

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
