# creating secrets for Mosquitto users

To update or add a user's password in mosquittos configuration, you need to create a secret for the user. The secret is a base64 encoded string of the user's password. You can create the secret with the following command:

```bash
cd ../../
oc create secret generic --dry-run mosquitto --from-file secrets/passwd -o yaml >secrets/mosquitto-passwd.yaml
```

The secret must hen be encrypted using SOPS:

```bash
cd manfiests/
sops --encrypt --output-type=yaml --input-type yaml ../secrets/mosquitto-passwd.yaml >mosquitto/sops-vault.yaml
```

directories do matter, as they might contain config files `.sops.yaml` ;)
