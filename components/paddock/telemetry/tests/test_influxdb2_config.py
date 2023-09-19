import os

import pytest

from paddock.exceptions import RuntimeEnvironmentConfigurationIncompleteError
from telemetry.utils import get_influxdb2_config


@pytest.mark.unittest
class TestInfluxDB2Config:
    def test_getinfluxdb2_config(self):
        with pytest.raises(RuntimeEnvironmentConfigurationIncompleteError) as excinfo:
            (org, token, url) = get_influxdb2_config()
            assert org == "b4mad"
        assert str(excinfo.value) == "missing environment variable: B4MAD_RACING_INFLUX_TOKEN"

        with pytest.raises(RuntimeEnvironmentConfigurationIncompleteError) as excinfo:
            os.environ["B4MAD_RACING_INFLUX_TOKEN"] = "test"

            (org, token, url) = get_influxdb2_config()

            assert org == "b4mad"
            assert token == "test"

        assert str(excinfo.value) == "missing environment variable: INFLUXDB2_SERVICE_HOST"

        os.environ["B4MAD_RACING_INFLUX_ORG"] = "test"
        os.environ["B4MAD_RACING_INFLUX_TOKEN"] = "test"
        os.environ["INFLUXDB2_SERVICE_HOST"] = "test"

        (org, token, url) = get_influxdb2_config()

        assert org == "test"
        assert token == "test"
        assert url == "https://test:8086"
