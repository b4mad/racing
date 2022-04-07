# B4mad racing

## docker-compose stack

```
cd docker-compose
docker-compose up
```

## influx
https://github.com/InfluxCommunity/InfluxDBv2_Telegraf_Docker

Go to http://localhost:8086/ and login with [configuration.env](docker-compose/configuration.env)
and explore the racing bucket

## telegraf

```
docker-compose exec telegraf cat /tmp/metrics.out
```

## mqtt
### mosquitto

```
docker-compose exec mosquitto mosquitto_pub  -u admin -P admin -t racing -m '{"a": 5}'
```

https://github.com/kevinboone/mosquitto-openshift

### paho

publish stuff

```
pipenv run python ./client_pub_opts.py -t racing -H localhost -u admin -p admin -N 10
```

https://github.com/eclipse/paho.mqtt.python
