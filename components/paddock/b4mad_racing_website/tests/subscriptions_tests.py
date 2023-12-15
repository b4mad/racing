from django.test import TestCase
from django.urls import reverse

from .factories import CopilotFactory, UserFactory


class ProfileSubscriptionsUpdateViews(TestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user1.profile.mqtt_drivername = "user1"
        self.user1.save()
        self.user2 = UserFactory()
        self.user2.profile.mqtt_drivername = "user2"
        self.user2.save()

        self.copilot1 = CopilotFactory()
        self.copilot2 = CopilotFactory()
        self.copilot3 = CopilotFactory()
        self.copilot4 = CopilotFactory()
        self.copilot5 = CopilotFactory()

    def test_profile_subscriptions_update_view_does_not_accept_post_or_get(self):
        self.client.force_login(self.user1)

        response = self.client.post(
            reverse("profile-subscriptions", args=[self.user1.username]),
            data={"copilot_id": self.copilot1.id},
            content_type="application/json",
        )
        assert response is not None
        assert response.status_code == 405

        response = self.client.get(
            reverse("profile-subscriptions", args=[self.user1.username]),
            data={"copilot_id": self.copilot1.id},
        )
        assert response is not None
        assert response.status_code == 405

    def test_profile_subscriptions_update_view_put_only_accepts_json(self):
        self.client.force_login(self.user1)

        response = self.client.put(
            reverse("profile-subscriptions", args=[self.user1.username]),
            data={"copilot_id": self.copilot1.id},
        )
        assert response is not None
        assert response.status_code == 415
        assert response.json()["status"] == "error"
        assert response.json()["message"] == "Invalid content type"

    def test_auth_user_can_enable_subscription(self):
        self.client.force_login(self.user1)

        assert self.user1.profile.subscriptions.count() == 0

        response = self.client.put(
            reverse("profile-subscriptions", args=[self.user1.username]),
            content_type="application/json",
            data={"copilot_id": self.copilot1.id},
        )
        assert response is not None
        assert response.status_code == 204
        assert self.user1.profile.subscriptions.count() == 1
        assert self.user1.profile.subscriptions.first() == self.copilot1

    def test_unauth_user_can_not_enable_subscription(self):
        response = self.client.put(
            reverse("profile-subscriptions", args=[self.user1.username]),
            data={"copilot_id": self.copilot1.id},
        )
        assert response is not None
        assert response.status_code == 302

    # TODO: Implement this test
    # def test_auth_can_not_enable_subscription_for_copilot_with_no_mqtt_drivername(self):
    #    raise NotImplementedError

    # TODO: Implement this test
    # def test_auth_user_can_disable_subscription(self):
    #    raise NotImplementedError

    def test_auth_user_can_not_enable_subscription_for_other_user(self):
        self.client.force_login(self.user1)

        response = self.client.put(
            reverse("profile-subscriptions", args=[self.user2.username]),
            data={"copilot_id": self.copilot1.id},
        )
        assert response is not None
        assert response.status_code == 403
        assert response.json()["status"] == "error"
        assert response.json()["message"] == "You can't update another user's profile"

    def test_auth_user_can_not_enable_subscription_of_non_existing_copilot(self):
        self.client.force_login(self.user1)

        response = self.client.put(
            reverse("profile-subscriptions", args=[self.user1.username]),
            content_type="application/json",
            data={"copilot_id": 999},
        )
        assert response is not None
        assert response.status_code == 404
        assert response.json()["status"] == "error"
        assert response.json()["message"] == "Copilot does not exist"

    def test_auth_user_can_not_disable_subscription_of_non_existing_copilot(self):
        self.client.force_login(self.user1)

        response = self.client.delete(
            reverse("profile-subscriptions", args=[self.user1.username]),
            content_type="application/json",
            data={"copilot_id": 999},
        )
        assert response is not None
        assert response.status_code == 404
        assert response.json()["status"] == "error"
        assert response.json()["message"] == "Copilot does not exist"

    # TODO: Implement this test
    # def test_unsubscribe_on_empty_subscriptions_does_not_fail(self):
    #     raise NotImplementedError
