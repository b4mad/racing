import csv
import os
import sys
from django.core.management.base import BaseCommand
from telemetry.models import Game, Car, Track, FastLap
from telemetry.pitcrew.crew import Crew


class Command(BaseCommand):
    help = "start pitcrew"

    def add_arguments(self, parser):
        parser.add_argument("-i", "--import-csv", nargs="*", type=str, default=None)

    def handle(self, *args, **options):
        if options["import_csv"]:
            for csv_file in options["import_csv"]:
                basename = os.path.basename(csv_file).split(".")[0]
                car, track = basename.split("-")
                game, created = Game.objects.get_or_create(name="iRacing")
                rcar, created = Car.objects.get_or_create(name=car, game=game)
                rtrack, created = Track.objects.get_or_create(name=track, game=game)
                fast_lap, created = FastLap.objects.get_or_create(
                    car=rcar, track=rtrack, game=game
                )

                with open(csv_file, mode="r") as infile:
                    reader = csv.DictReader(infile)
                    for row in reader:
                        brakepoint = {
                            "start": 0,
                            "end": 0,
                            "mark": "",
                            "turn_in": 0,
                            "force": 0,
                            "gear": 0,
                            "speed": 0,
                            "stop": 0,
                            "accelerate": 0,
                        }
                        for key in row:
                            if row[key]:
                                if key == "mark" or key == "turn":
                                    brakepoint[key] = row[key]
                                else:
                                    brakepoint[key] = int(row[key])
                            else:
                                brakepoint[key] = 0
                        print(brakepoint)
                        segment, created = fast_lap.fast_lap_segments.get_or_create(
                            start=brakepoint["start"],
                            end=brakepoint["end"],
                            mark=brakepoint["mark"],
                            gear=brakepoint["gear"],
                            force=brakepoint["force"],
                            speed=brakepoint["speed"],
                            stop=brakepoint["stop"],
                            accelerate=brakepoint["accelerate"],
                            brake=brakepoint["brake"],
                        )
                        print(segment)
                        print(created)

                self.stdout.write(
                    self.style.SUCCESS('Successfully imported "%s"' % csv_file)
                )
                sys.exit(0)

        crew = Crew()
        crew.run()
