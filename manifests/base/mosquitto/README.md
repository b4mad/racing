# creating secrets for Mosquitto users

To update or add a user's password in mosquittos configuration, you need to create a secret for the user. The secret is a base64 encoded string of the user's password. You can create the passwd file with the following command:

```
mosquitto_passwd -c -b mosquitto.passwd admin admin
mosquitto_passwd -b mosquitto.passwd crewchief crewchief
```

Then add the contents of `mosquitto.passwd` to the passwords field in secret/secret.yaml
