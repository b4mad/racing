# Create Secret for Telegraf configuration

```shell
cd .. # should be in manifests now
oc create secret generic --dry-run telegraf \
  --from-literal=input-username=crewchief \
  --from-literal=input-password=crewchief \
  --from-literal=token=KHxFBLKlcfv3 \
  -o yaml >../secrets/telegraf.yaml
sops --encrypt --output-type=yaml --input-type yaml ../secrets/telegraf.yaml >telegraf/overlays/smaug/sops-vault.enc.yaml
```
