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

    if _INFLUXDB2_SERVICE_HOST is None:
        raise RuntimeEnvironmentConfigurationIncompleteError(
            "INFLUXDB2_SERVICE_HOST",
        )

    url = f"https://{_INFLUXDB2_SERVICE_HOST}:{_INFLUXDB2_SERVICE_PORT}"

    return (org, token, url)
