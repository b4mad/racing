# B4mad racing

## docker-compose stack

```
cd docker-compose
docker-compose up
```

### influx

Go to http://localhost:8086/ and login with [configuration.env](docker-compose/configuration.env)
and explore the racing bucket

* https://github.com/InfluxCommunity/InfluxDBv2_Telegraf_Docker

### telegraf

```
docker-compose exec telegraf cat /tmp/metrics.out
```

### mosquitto

publish stuff

```
pipenv run python ./client_pub_opts.py -t racing -H localhost -u admin -p admin -N 10
docker-compose exec mosquitto mosquitto_pub  -u admin -P admin -t racing -m '{"a": 5}'
docker-compose exec mosquitto mosquitto_pub  -u admin -P admin -t racing -m "`cat ../sample-small.json`"
```

* https://github.com/eclipse/paho.mqtt.python
* https://github.com/kevinboone/mosquitto-openshift

## links

* https://github.com/viper4gh/CREST2

## TODO

* add certs to mosquitto

