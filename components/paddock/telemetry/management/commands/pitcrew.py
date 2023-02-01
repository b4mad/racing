from django.core.management.base import BaseCommand
from telemetry.models import Coach, Driver, FastLap
from telemetry.pitcrew.crew import Crew


class Command(BaseCommand):
    help = "start pitcrew"

    def add_arguments(self, parser):
        parser.add_argument("-c", "--coach", nargs="?", type=str, default=None)
        parser.add_argument("-r", "--replay", action="store_true")
        parser.add_argument("-d", "--delete-driver-fastlaps", action="store_true")

    def handle(self, *args, **options):
        crew = Crew()
        if options["coach"]:
            driver = Driver.objects.get(name=options["coach"])
            coach, created = Coach.objects.get_or_create(driver=driver)
            crew.start_coach(driver.name, coach, debug=True, replay=options["replay"])
        elif options["delete_driver_fastlaps"]:
            # get all fastlaps where driver is not empty
            FastLap.objects.filter(driver__isnull=False).delete()
        else:
            crew.run()
