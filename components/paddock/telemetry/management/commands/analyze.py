from django.core.management.base import BaseCommand
from telemetry.models import Game, Driver, Car, Track, SessionType
from telemetry.influx import Influx


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

        # # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )

    def handle(self, *args, **options):
        # Driver.objects.all().delete()
        # Game.objects.all().delete()
        i = Influx()

        for session_id in i.sessions():
            print(session_id)
            records = i.session(session_id)
            try:
                record = next(records)
            except StopIteration:
                continue
            print(record)

            game, created = Game.objects.get_or_create(name=record["GameName"])
            driver, created = Driver.objects.get_or_create(name=record["user"])
            car, created = Car.objects.get_or_create(name=record["CarModel"], game=game)
            track, created = Track.objects.get_or_create(
                name=record["TrackCode"], game=game
            )
            session_type, created = SessionType.objects.get_or_create(
                type=record["SessionTypeName"]
            )
            session, created = driver.session_set.get_or_create(
                session_id=record["SessionId"],
                session_type=session_type,
                car=car,
                track=track,
                game=game,
                defaults={"start": record["_time"], "end": record["_time"]},
            )
            lap, created = session.lap_set.get_or_create(
                number=record["CurrentLap"],
                start=record["_time"],
            )

            r = record
            for record in records:
                if r["CurrentLap"] != record["CurrentLap"]:
                    if track.length < r["DistanceRoundTrack"]:
                        track.length = r["DistanceRoundTrack"]
                        track.save()

                    lap.time = r["CurrentLapTime"]
                    lap.length = r["DistanceRoundTrack"]
                    lap.save()

                    lap, created = session.lap_set.get_or_create(
                        number=record["CurrentLap"],
                        start=record["_time"],
                    )

                r = record
            session.end = record["_time"]
            session.save()
