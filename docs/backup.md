# Backup

This will invalidate the token, so you need to create a new one after restoring the backup.
Check the scripts/setup_secrets.sh for details.

```
oc debug job/backup -c influxdb-backup
export INFLUX_TOKEN="${INFLUXDB_ADMIN_USER_TOKEN}"
export INFLUX_HOST="http://influxdb2.b4mad-racing.svc:8086"
export INFLUX_ORG="b4mad"
influx bucket list
influx bucket delete --name racing
influx restore 20230712_020005/
```
