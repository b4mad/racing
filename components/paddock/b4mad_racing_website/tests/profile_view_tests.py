from django.test import TestCase
from django.urls import reverse

from .factories import UserFactory


class ProfileDetailsViews(TestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user1.profile.mqtt_drivername = "user1"
        self.user1.save()

        self.user2 = UserFactory()
        self.user2.profile.verified = False
        self.user2.profile.mqtt_drivername = "user2"
        self.user2.save()

        # user3 is not publicly visible
        self.user3 = UserFactory()
        self.user3.profile.publicly_visible = False
        self.user3.profile.mqtt_drivername = "user3"
        self.user3.save()

    def test_unauth_view_of_public_profile_shows_profile(self):
        response = self.client.get(reverse("profile", args=[self.user1.username]))
        assert response is not None

        self.assertTemplateUsed(response, "profile/details.html")
        self.assertInHTML(f"{self.user1.username}", str(response.content))

    def test_viewing_nonpublic_profile_redirects_to_home_raising_message(self):
        # let's have a look at user3's profile
        response = self.client.get(reverse("profile", args=[self.user3.username]))
        assert response is not None
        self.assertRedirects(response, reverse("home"))

    def test_auth_viewing_nonpublic_own_profile(self):
        self.client.force_login(self.user3)

        # let's have a look at my own profile
        response = self.client.get(reverse("profile", args=[self.user3.username]))
        assert response is not None

        # we should get a 200
        assert response.status_code == 200
        self.assertTemplateUsed(response, "profile/details.html")

    def test_viewing_my_self(self):
        self.client.force_login(self.user1)

        # let's have a look at user1's profile
        response = self.client.get(reverse("profile", args=[self.user1.username]))
        assert response is not None
        self.assertHTMLEqual(str(response.status_code), "200")

        # and it should include the mqtt_drivername
        self.assertTemplateUsed(response, "profile/details.html")
        self.assertInHTML(f"mqtt driver name: {self.user1.profile.mqtt_drivername}", str(response.content))

    def test_viewing_other_profile_should_not_show_mqtt_drivername(self):
        self.client.force_login(self.user1)

        # let's have a look at user2's profile
        response = self.client.get(reverse("profile", args=[self.user2.username]))
        assert response is not None
        self.assertHTMLEqual(str(response.status_code), "200")

        # and it should not include the mqtt_drivername
        self.assertTemplateUsed(response, "profile/details.html")
        self.assertNotContains(response, f"mqtt driver name: {self.user2.profile.mqtt_drivername}", html=True)
