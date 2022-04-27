# B4mad racing

https://b4mad.racing

## SimHub installation

Install [SimHub](https://www.simhubdash.com/) and install the [MQTT Publisher plugin](https://nightly.link/durandom/SimHub-MQTT-Publisher/workflows/dotnet/main/release-artifact.zip) by unziping the contents into the SimHub folder at `C:\Program Files (x86)\SimHub`

In the plugin settings you should adjust the topic to include your username, i.e. replace `durandom` with your name

```json
{
  "Server": "telemetry.b4mad.racing",
  "Topic": "racing/durandom",
  "Login": "admin",
  "Password": "admin",
  "Port": 31883
}
```


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
docker compose exec telegraf cat /tmp/metrics.out
docker compose restart telegraf
```

### mosquitto

publish stuff

```
docker-compose exec mosquitto mosquitto_pub  -u admin -P admin -t racing -m '{"a": 5}'
docker-compose exec mosquitto mosquitto_pub  -u admin -P admin -t racing -m "`cat ../sample-small.json`"
```

subscribe
```
docker-compose exec mosquitto mosquitto_sub  -u admin -P admin -t racing/\# -d
docker-compose exec mosquitto mosquitto_sub  -p 31883 -h telemetry.b4mad.racing -u admin -P admin -t racing/\# -d
```

* https://github.com/eclipse/paho.mqtt.python
* https://github.com/kevinboone/mosquitto-openshift

### grafana

Export data sources
```
curl -s "http://localhost:3000/api/datasources" -u admin:admin | jq -c -M '.[]'
```

## Data Format

```
Measurement: session
Tags: game, qualifying, race
Fields: leaderboard, leader, incident

Measurement: laps
Tags: driver_uid, car_name, circuit
Fields: rpm, speed, location
```

## links

* https://github.com/viper4gh/CREST2

## TODO

* add certs to mosquitto

