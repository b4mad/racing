from django.test import TransactionTestCase

from paddock.exceptions import RuntimeEnvironmentConfigurationIncompleteError


class TestInfluxDB2Config(TransactionTestCase):
    def test_env(self):
        raise RuntimeEnvironmentConfigurationIncompleteError("InfluxDB2Config")
