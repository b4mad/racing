from django.test import Client, TestCase
from django.urls import reverse


class TestFrontpage(TestCase):
    def test_ok(self):
        """The app returns 200 OK for a user."""
        client = Client()

        response = client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
