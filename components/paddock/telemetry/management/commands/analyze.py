import csv
import os
from django.core.management.base import BaseCommand
from telemetry.models import Game, Driver, Car, Track, SessionType, Lap, FastLap
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

        # add optional argument for game, track and car
        parser.add_argument(
            "-g",
            "--game",
            nargs="?",
            type=str,
            default=None,
            help="game name to analyze",
        )
        parser.add_argument(
            "-t",
            "--track",
            nargs="?",
            type=str,
            default=None,
            help="track name to analyze",
        )
        parser.add_argument(
            "-c",
            "--car",
            nargs="?",
            type=str,
            default=None,
            help="car name to analyze",
        )
        parser.add_argument("-i", "--import-csv", nargs="*", type=str, default=None)
        parser.add_argument(
            "-n", "--new", action="store_true", help="only analyze new coaches"
        )
        parser.add_argument(
            "-s",
            "--save-csv",
            nargs="?",
            type=str,
            default=None,
            help="save to csv",
        )

    def import_csv(self, options):
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

    def handle(self, *args, **options):
        if options["save_csv"]:
            csv_file = open(options["save_csv"], "w")
            # open a file for appending
            csv_writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "game",
                    "session",
                    "track",
                    "car",
                    "lap",
                    "start",
                    "end",
                    "time",
                    "length",
                    "valid",
                ],
            )
            csv_writer.writeheader()

        if options["import_csv"]:
            self.import_csv(options["import_csv"])

        if options["lap_ids"]:
            laps = Lap.objects.filter(pk__in=options["lap_ids"])
            fl = FastLapAnalyzer(laps)
            track_info = fl.analyze()
            if track_info:
                self.save_fastlap(
                    track_info,
                    car=laps[0].car,
                    track=laps[0].track,
                    game=laps[0].track.game,
                )
            exit(0)

        where = []
        if options["game"]:
            game = Game.objects.get(name=options["game"])
            where.append(f"game='{game.pk}'")
        if options["track"]:
            track = Track.objects.get(name=options["track"])
            where.append(f" track_id={track.pk}")
        if options["car"]:
            car = Car.objects.get(name=options["car"])
            where.append(f"car_id={car.pk}")

        where_clause = ""
        if where:
            where_clause = "where " + " and ".join(where)

        sql = f"select count(id) as c, track_id, car_id from telemetry_lap {where_clause} group by track_id, car_id"

        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        for count, track_id, car_id in rows:
            car = Car.objects.get(id=car_id)
            track = Track.objects.get(id=track_id)
            game = car.game
            if game.name == "RaceRoom":
                logging.info("RaceRoom not supported, because no SteeringAngle")
                continue
            if game.name == "Assetto Corsa Competizione":
                logging.info(
                    "Assetto Corsa Competizione not supported, because no SteeringAngle"
                )
                continue
            if car.name == "Unknown":
                logging.info(f"Car {car.name} not supported, skipping")
                continue

            if options["new"]:
                if FastLap.objects.filter(
                    car=car, track=track, game=game, driver=None
                ).exists():
                    logging.info(
                        f"Fastlap already exists for {game.name} / {track.name} / {car.name}"
                    )
                    continue

            logging.info(f"{count} laps for {game.name} / {track.name} / {car.name}")

            laps = Lap.objects.filter(
                track=track, car=car, length__gt=track.length - 20, time__gt=20
            ).order_by("time")[:10]

            if laps.count() > 0:
                lap = laps[0]
                fast_time = lap.time
                fast_laps = [lap]
                # threshold is 120% of the fastest lap
                threshold = fast_time * 1.2

                for lap in laps[1:]:
                    if lap.time <= threshold:
                        # print(f"{lap.time} is <= {threshold}")
                        fast_laps.append(lap)

                if options["save_csv"]:
                    for lap in fast_laps:
                        row = {
                            "game": game.name,
                            "session": lap.session.session_id,
                            "track": track.name,
                            "car": lap.car.name,
                            "lap": lap.number,
                            "start": lap.start,
                            "end": lap.end,
                            "time": lap.time,
                            "length": lap.length,
                            "valid": lap.valid,
                        }
                        csv_writer.writerow(row)
                else:
                    fl = FastLapAnalyzer(fast_laps)
                    track_info = fl.analyze()
                    if track_info:
                        self.save_fastlap(track_info, car=car, track=track, game=game)

        if options["save_csv"]:
            csv_file.close()

    def save_fastlap(self, track_info, car=None, track=None, game=None):
        fast_lap, created = FastLap.objects.get_or_create(
            car=car, track=track, game=game, driver=None
        )
        fast_lap.fast_lap_segments.all().delete()
        i = 1
        for brakepoint in track_info:
            print(brakepoint)
            segment, created = fast_lap.fast_lap_segments.get_or_create(
                turn=i,
                start=brakepoint["start"],
                end=brakepoint["end"],
                brake=brakepoint["brake"],
                force=brakepoint["force"],
                gear=brakepoint["gear"],
                speed=brakepoint["speed"],
                stop=brakepoint["stop"],
                accelerate=brakepoint["accelerate"],
                # mark=brakepoint["mark"],
            )
            i += 1

    def handle_influx(self, *args, **options):
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
