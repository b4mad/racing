from b4mad_racing_website.models import CopilotInstance
from django.test import TestCase

from .factories import CopilotFactory, UserFactory


class CopilotsOverviewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.save()

        self.copilot = CopilotFactory()

    def test_unset_mqtt_drivername_results_in_misconfigured_copilot(self):
        # the user has not configured a mqtt_drivername
        assert self.user.profile.mqtt_drivername == ""
        self.user.profile.save()
        assert self.user.profile.subscriptions.count() == 0

        self.user.profile.subscribe_copilot(self.copilot.id)
        assert self.user.profile.subscriptions.count() == 1

        ci = CopilotInstance.objects.get(driver=self.user.profile, copilot=self.copilot)
        self.assertIsNotNone(ci)
        assert ci.status == CopilotInstance.Status.MISCONFIGURED

    def test_set_mqtt_drivername_results_in_configured_copilot(self):
        self.user.profile.mqtt_drivername = "tester"
        self.user.profile.subscribe_copilot(self.copilot.id)
        self.user.profile.save()
        assert self.user.profile.subscriptions.count() == 1

        ci = CopilotInstance.objects.get(driver=self.user.profile, copilot=self.copilot)
        self.assertIsNotNone(ci)
        assert ci.status == CopilotInstance.Status.CONFIGURED

    def test_unsubscribe_from_copilot_results_in_deleted_copilotinstance(self):
        self.user.profile.mqtt_drivername = "tester"
        self.user.profile.save()
        self.user.profile.subscribe_copilot(self.copilot.id)

        self.user.profile.unsubscribe_copilot(self.copilot.id)
        assert self.user.profile.subscriptions.count() == 0

        with self.assertRaises(CopilotInstance.DoesNotExist):
            CopilotInstance.objects.get(driver=self.user.profile, copilot=self.copilot)
