import os

from paddock.exceptions import RuntimeEnvironmentConfigurationIncompleteError


def get_influxdb2_config() -> tuple[str, str, str] | RuntimeEnvironmentConfigurationIncompleteError:
    """Get InfluxDB2 configuration from environment variables."""
    org = os.environ.get("B4MAD_RACING_INFLUX_ORG", "b4mad")

    _INFLUXDB2_TOKEN = os.environ.get("B4MAD_RACING_INFLUX_TOKEN")  # noqa: N806

    if _INFLUXDB2_TOKEN is None or _INFLUXDB2_TOKEN == "":
        raise RuntimeEnvironmentConfigurationIncompleteError(
            "B4MAD_RACING_INFLUX_TOKEN",
        )

    token = _INFLUXDB2_TOKEN

    _INFLUXDB2_SERVICE_HOST = os.environ.get("INFLUXDB2_SERVICE_HOST")  # noqa: N806
    _INFLUXDB2_SERVICE_PORT = os.environ.get("INFLUXDB2_SERVICE_PORT", 8086)  # noqa: N806
    _INFLUXDB2_SERVICE_PROTOCOL = os.environ.get("INFLUXDB2_SERVICE_PROTOCOL", "http")  # noqa: N806

    if _INFLUXDB2_SERVICE_HOST is None:
        raise RuntimeEnvironmentConfigurationIncompleteError(
            "INFLUXDB2_SERVICE_HOST",
        )

    url = f"{_INFLUXDB2_SERVICE_PROTOCOL}://{_INFLUXDB2_SERVICE_HOST}:{_INFLUXDB2_SERVICE_PORT}/"

    return (org, token, url)


def get_mqtt_config() -> tuple[str, int, str, str] | RuntimeEnvironmentConfigurationIncompleteError:
    """Get MQTT configuration from environment variables."""
    _B4MAD_RACING_MQTT_HOST = os.environ.get("MOSQUITTO_MQTT_SERVICE_HOST")  # noqa: N806
    _B4MAD_RACING_MQTT_PORT = int(os.environ.get("MOSQUITTO_MQTT_SERVICE_PORT", 1883))  # noqa: N806
    _B4MAD_RACING_MQTT_USER = os.environ.get("B4MAD_RACING_MQTT_USER", "crewchief")  # noqa: N806
    _B4MAD_RACING_MQTT_PASSWORD = os.environ.get("B4MAD_RACING_MQTT_PASSWORD", "crewchief")  # noqa: N806

    if _B4MAD_RACING_MQTT_HOST is None:
        raise RuntimeEnvironmentConfigurationIncompleteError("MOSQUITTO_MQTT_SERVICE_HOST")

    return (
        _B4MAD_RACING_MQTT_HOST,
        _B4MAD_RACING_MQTT_PORT,
        _B4MAD_RACING_MQTT_USER,
        _B4MAD_RACING_MQTT_PASSWORD,
    )
