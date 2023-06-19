from django.core.management.base import BaseCommand
from django.db import transaction

from telemetry.factories import DriverFactory
from telemetry.models import Driver


class Command(BaseCommand):
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        Driver.objects.all().delete()

        self.stdout.write("Creating new data...")
        people = []
        for _ in range(50):
            driver_factory = DriverFactory()
            people.append(driver_factory)
