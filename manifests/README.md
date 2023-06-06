# Deploy Telemetry infrastructure

the structure of this folder is inspired by <https://github.com/kostis-codefresh/gitops-environment-promotion>

## creating secrets

We are using [sealed secrets](https://sealed-secrets.netlify.app/) being deployed via ArgoCD, a sops-encrypted version
is kept to generate the sealed secrets and keep them human-readable.

Creating sealed secrets from an env-file...

```shell
kubectl --namespace b4mad-racing --dry-run=client \
    create secret generic paddock-settings \
    --from-env-file .env \
    --output yaml \
| kubeseal --controller-namespace=sealed-secrets \
    --format yaml \
> manifests/env/phobos-test/paddock-settings.yaml
```

or via the sops-encrypted source:

```shell
sops --decrypt manifests/env/phobos/paddock-settings.enc.yaml \
| kubeseal --controller-namespace=sealed-secrets \
    --format yaml \
> manifests/env/phobos-test/paddock-settings.yaml
```

Make sure, that the input to `kubeseal` is using the correct namespace!

## Deploying to a new OpenShift cluster

```shell
kustomize build manifests/env/phobos | oc apply -f -
sleep 60
scripts/setup_buckets.sh
scripts/setup_secrets.sh
scripts/setup_trigger_updates.sh
scripts/open.sh paddock
scripts/open.sh telemetry
scripts/open.sh grafana
```
