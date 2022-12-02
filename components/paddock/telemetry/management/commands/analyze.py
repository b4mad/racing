from django.core.management.base import BaseCommand
from telemetry.models import Game, Driver, Car, Track, SessionType, Lap
from telemetry.influx import Influx
from telemetry.fast_lap_analyzer import FastLapAnalyzer
import logging
from django.db import connection


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        # add argument for list of lap ids as integers separated by commas
        parser.add_argument(
            "-l",
            "--lap-ids",
            nargs="+",
            type=int,
            default=None,
            help="list of lap ids to analyze",
        )

    def handle(self, *args, **options):
        if options["lap_ids"]:
            laps = Lap.objects.filter(pk__in=options["lap_ids"])
            fl = FastLapAnalyzer(laps)
            fl.analyze()
            exit(0)

        sql = "select count(id) as c, track_id, car_id from telemetry_lap group by track_id, car_id"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        for count, track_id, car_id in rows:
            car = Car.objects.get(id=car_id)
            track = Track.objects.get(id=track_id)
            game = car.game
            logging.info(f"{count} laps for {game.name} / {track.name} / {car.name}")

            if game.name == "RaceRoom":
                logging.info("RaceRoom not supported, because no SteeringAngle")
                continue
            if game.name == "Assetto Corsa Competizione":
                logging.info(
                    "Assetto Corsa Competizione not supported, because no SteeringAngle"
                )
                continue

            laps = Lap.objects.filter(
                track=track, car=car, length__gt=track.length - 5, time__gt=10
            ).order_by("time")[:10]

            if laps.count() > 0:
                lap = laps[0]
                fast_time = lap.time
                fast_laps = [lap]
                # threshold is 120% of the fastest lap
                threshold = fast_time * 1.2

                for lap in laps[1:]:
                    if lap.time <= threshold:
                        fast_laps.append(lap)

                fl = FastLapAnalyzer(laps)
                fl.analyze()

    def handle_inlfux(self, *args, **options):
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
            session, created = driver.sessions.get_or_create(
                session_id=record["SessionId"],
                session_type=session_type,
                car=car,
                track=track,
                game=game,
                defaults={"start": record["_time"], "end": record["_time"]},
            )
            lap, created = session.laps.get_or_create(
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

                    lap, created = session.laps.get_or_create(
                        number=record["CurrentLap"],
                        start=record["_time"],
                    )

                r = record
            session.end = record["_time"]
            session.save()
