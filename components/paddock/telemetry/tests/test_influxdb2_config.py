import os

import pytest
from django.test import TransactionTestCase

from paddock.exceptions import RuntimeEnvironmentConfigurationIncompleteError
from telemetry.utils import get_influxdb2_config


class TestInfluxDB2Config(TransactionTestCase):
    @pytest.fixture()
    def setup(self):
        os.environ["B4MAD_RACING_INFLUX_ORG"] = ""
        os.environ["B4MAD_RACING_INFLUX_TOKEN"] = ""
        os.environ["INFLUXDB2_SERVICE_HOST"] = ""
        os.environ["INFLUXDB2_SERVICE_PORT"] = ""

    def test_getinfluxdb2_config(self):
        with pytest.raises(RuntimeEnvironmentConfigurationIncompleteError) as excinfo:
            (org, token, url) = get_influxdb2_config()
            assert org == "b4mad"
        assert str(excinfo.value) == "missing environment variable: INFLUXDB2_SERVICE_HOST"

        with pytest.raises(RuntimeEnvironmentConfigurationIncompleteError) as excinfo:
            os.environ["INFLUXDB2_SERVICE_HOST"] = "test"

            (org, token, url) = get_influxdb2_config()

            assert org == "b4mad"
            assert url == "https://test:8086"

        assert str(excinfo.value) == "missing environment variable: B4MAD_RACING_INFLUX_TOKEN"
