# B4mad racing

https://b4mad.racing - https://pitwall.b4mad.racing

### A telemetry data collection pipeline for simracers :racing_car:

The b4mad client is implemented via a [SimHub](https://www.simhubdash.com/) plugin. This means that b4mad can take data
in from any simulation that SimHub supports. The plugin will send your simulator telemetry data to the b4mad cloud. You
can then visualize your telemetry data using our dashboarding tooling.

![architecture](docs/architecture.png)

## Installation

1. Install [SimHub](https://www.simhubdash.com/)
1. Download the [MQTT Publisher
   plugin](https://nightly.link/durandom/SimHub-MQTT-Publisher/workflows/dotnet/main/release-artifact.zip)
1. Unzip the contents of the MQTT publisher plugin into the SimHub folder. It is
   probably `C:\Program Files (x86)\SimHub` unless you used an alternate install
   location.
1. Run SimHub and go to the plugin settings. You will find them in the left-navigation of SimHub under the `MQTT Publisher` heading.
1. Change the `MQTT Topic` to include a username for yourself.

    At this time there is no user registration, so anything goes. But avoid special characters, emoji, unicode, and etc.

    Good: `racing/paul_ricard` (no spaces)

    Bad: `racing/i am a hero!` (spaces, special characters)

    Also bad: `racingdriver64` (missing `racing/`)

    You **MUST** leave `racing/` as the prefix.

![simhub](docs/simhub.png)

Once complete, any time you run your simulator you will be sending data to
b4mad. See the Visualization section for information about how to look at your
data.
## Visualization

Head over to the [B4mad Pitwall](https://pitwall.b4mad.racing) and explore your
recent sessions or signup for an account to create new dashboards.

![grafana](docs/grafana.png)

Check out the [flux scratchpad](flux/SCRATCH.flux) for some
[flux](https://docs.influxdata.com/flux/v0.x/) query examples.


# Hacking

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
