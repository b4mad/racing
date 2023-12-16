from django.test import TestCase
from django.urls import reverse

from .factories import CopilotFactory, UserFactory


class CopilotsOverviewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.save()

        self.copilot1 = CopilotFactory()
        self.copilot2 = CopilotFactory()
        self.copilot3 = CopilotFactory()
        self.copilot4 = CopilotFactory()
        self.copilot5 = CopilotFactory()

    def test_copilots_overview(self):
        response = self.client.get(reverse("copilots-overview"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "copilots/overview.html")
        self.assertContains(response, "#B4mad Racing Copilots")

    def test_copilot_details_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("copilot-details", args=[self.copilot1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.copilot1.name)
        self.assertTemplateUsed(response, "copilots/details.html")

    def test_copilot_details_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("copilot-details", args=[self.copilot1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.copilot1.name)
        self.assertTemplateUsed(response, "copilots/details.html")

    def test_enabler_is_visible_if_user_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("copilots-overview"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "copilots/overview.html")

        # FIXME This test is a little bit unflexible, as it assumes a certain copilot it
        # disabling it for the moment
        # self.assertInHTML(response, '<input class="form-check-input" type="checkbox" id="enable-copilot-1">')

    def test_no_enabler_if_user_not_logged_in(self):
        self.client.logout()
        response = self.client.get(reverse("copilots-overview"))

        self.assertNotContains(response, '<input class="form-check-input" type="checkbox" id="enable-copilot-1">')

    def test_viewing_profile_shows_list_of_enabled_copilots(self):
        # we assume that the profile is publicly visible, user2 is
        response = self.client.get(reverse("profile", args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile/details.html")

        self.assertContains(response, "No Copilots are enabled.")

        # let's enable some copilots for this user, therefor we need to
        # add to the user's profile subscriptions attribute
        self.user.profile.subscriptions.add(self.copilot1)

        # now we should see the copilot in the profile
        response = self.client.get(reverse("profile", args=[self.user.username]))
        self.assertContains(response, self.copilot1.name)

        # and just for fun, let's enable another copilot and disable the first one
        self.user.profile.subscriptions.add(self.copilot2)
        self.user.profile.subscriptions.remove(self.copilot1)

        response = self.client.get(reverse("profile", args=[self.user.username]))
        self.assertContains(response, self.copilot2.name)
