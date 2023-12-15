import factory
from b4mad_racing_website.models import Copilot
from django.contrib.auth import get_user_model
from django.utils import timezone


class CopilotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Copilot

    name = factory.Faker("name")
    description = factory.Faker("text")
    published = factory.Faker("date_time", tzinfo=timezone.get_current_timezone())
    description = factory.Faker("text")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "password")
