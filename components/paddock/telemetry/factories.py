import factory
from factory.django import DjangoModelFactory

from .models import Driver


class DriverFactory(DjangoModelFactory):
    class Meta:
        model = Driver

    name = factory.Faker("name")
