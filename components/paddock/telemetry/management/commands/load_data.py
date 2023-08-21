import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

# from telemetry.factories import DriverFactory
from telemetry.models import Game, Landmark

# from django.db import transaction


class Command(BaseCommand):
    help = "Load data"

    def add_arguments(self, parser):
        parser.add_argument("--landmarks", action="store_true")

    def handle(self, *args, **options):
        if options["landmarks"]:
            self.landmarks()

    def landmarks(self):
        # Load track landmarks data
        data_file = Path(__file__).parent / "trackLandmarksData.json"
        with open(data_file) as f:
            landmarks_data = json.load(f)

        # delete all landmarks
        # Landmark.objects.all().delete()

        games_keys = {
            "acTrackNames": Game.objects.filter(name="Assetto Corsa (64 bit)").first(),
            "ams2TrackName": Game.objects.filter(name="Automobilista 2").first(),
            "irTrackName": Game.objects.filter(name="iRacing").first(),
            "accTrackName": Game.objects.filter(name="Assetto Corsa Competizione").first(),
        }

        # Iterate over each track's landmarks
        for track_data in landmarks_data["TrackLandmarksData"]:
            for key, game in games_keys.items():
                if key in track_data:
                    track_names = track_data[key]
                    # if track_name is an array, iterate over each track name
                    if not isinstance(track_names, list):
                        track_names = [track_names]

                    for track_name in track_names:
                        if not track_name:
                            logging.debug(f"!!! Empty track name for {game}")
                            continue
                        track, created = game.tracks.get_or_create(name=track_name)
                        logging.debug(f"{game}: {track}")
                        if created:
                            logging.debug(f"!!! Created new track: {track}")

                        # Create or update landmarks
                        for landmark_data in track_data["trackLandmarks"]:
                            # Try to find existing landmark
                            landmark, created = Landmark.objects.get_or_create(
                                name=landmark_data["landmarkName"], track=track, kind=Landmark.KIND_TURN, from_cc=True
                            )
                            logging.debug(f"  {landmark}")

                            # Update fields if needed
                            landmark.start = landmark_data["distanceRoundLapStart"]
                            landmark.end = landmark_data["distanceRoundLapEnd"]
                            landmark.is_overtaking_spot = landmark_data["isCommonOvertakingSpot"]

                            landmark.save()

            # break

    # @transaction.atomic
    # def devel_data(self, *args, **kwargs):
    #     self.stdout.write("Deleting old data...")
    #     Driver.objects.all().delete()

    #     self.stdout.write("Creating new data...")
    #     people = []
    #     for _ in range(50):
    #         driver_factory = DriverFactory()
    #         people.append(driver_factory)
