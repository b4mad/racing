import logging

from django.core.management.base import BaseCommand

from telemetry.fast_lap_analyzer import FastLapAnalyzer
from telemetry.influx import Influx
from telemetry.models import FastLap
from telemetry.racing_stats import RacingStats


class Command(BaseCommand):
    help = "Analyze telemetry"

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
        parser.add_argument("--from-bucket", nargs="?", type=str, default="racing")
        parser.add_argument("-n", "--new", action="store_true", help="only analyze new coaches")
        parser.add_argument("--copy-influx", action="store_true")
        parser.add_argument("--force-save", action="store_true")

    def handle(self, *args, **options):
        min_laps = 1
        max_laps = 10
        influx = Influx()
        racing_stats = RacingStats()
        influx_fast_sessions = set()
        from_bucket = options["from_bucket"]
        if options["copy_influx"]:
            influx_fast_sessions = influx.session_ids(bucket="fast_laps")

        # if options["lap_ids"]:
        #     laps = Lap.objects.filter(pk__in=options["lap_ids"])
        #     self.analyze_fast_laps(laps)
        #     return

        for game, car, track, count in racing_stats.known_combos_list(**options):
            logging.debug(f"{game} / {car} / {track} / {count} laps")
            laps = racing_stats.laps(game=game, car=car, track=track, valid=True)

            laps_count = laps.count()
            if laps_count < min_laps:
                logging.debug("... not enough laps")
                continue

            logging.debug(f"... found {laps_count} laps")

            valid_laps = list(laps)

            used_laps = self.analyze_fast_laps(
                valid_laps, min_laps=min_laps, max_laps=max_laps, force_save=options["force_save"]
            )

            if options["copy_influx"] and used_laps:
                sessions = set()
                for lap in used_laps:
                    sessions.add(lap.session)

                for session in sessions:
                    if session.session_id in influx_fast_sessions:
                        influx_fast_sessions.remove(session.session_id)
                        continue
                    logging.info(f"copying session {session.session_id} to fast_laps")
                    influx.copy_session(
                        session.session_id, start=session.start, end=session.end, from_bucket=from_bucket
                    )

        # if options["copy_influx"]:
        #     logging.debug(f"fast sessions to be deleted: {influx_fast_sessions}")

    def analyze_fast_laps(self, fast_laps, min_laps=1, max_laps=10, force_save=False):
        fl = FastLapAnalyzer(fast_laps)
        lap_ids = set([lap.id for lap in fast_laps])
        lap = fast_laps[0]
        car = lap.car
        track = lap.track
        game = lap.session.game
        fast_lap, created = FastLap.objects.get_or_create(car=car, track=track, game=game, driver=None)
        if fast_lap.data:
            previous_run_lap_ids = fast_lap.data.get("lap_ids", set())
            if previous_run_lap_ids == lap_ids and not force_save:
                logging.debug("same laps as previous run, skipping")
                return
        result = fl.analyze(min_laps=min_laps, max_laps=max_laps)

        if result:
            data = result[0]
            data["lap_ids"] = lap_ids
            used_laps = result[1]
            logging.debug(f"found {len(data['segments'])} sectors in {len(used_laps)} laps")

            delete_user_segments = True
            if fl.same_sectors:
                delete_user_segments = False

            self.save_fastlap(
                data,
                fast_lap=fast_lap,
                laps=used_laps,
                delete_user_segments=delete_user_segments,
                force_save=force_save,
            )
            return used_laps
        else:
            logging.error("no result")

    def save_fastlap(self, data, fast_lap=None, laps=[], delete_user_segments=True, force_save=False):
        if not laps:
            logging.error("no laps")
            return
        car = fast_lap.car
        track = fast_lap.track
        game = fast_lap.game

        if delete_user_segments or force_save:
            r = FastLap.objects.filter(car=car, track=track, game=game).exclude(driver=None).delete()
            logging.debug(f"Deleted {r} user segments")

        fast_lap, created = FastLap.objects.get_or_create(car=car, track=track, game=game, driver=None)
        current_laps = set(fast_lap.laps.all())
        new_laps = set(laps)
        got_new_laps = new_laps != current_laps

        fast_lap_data = fast_lap.data
        based_on_new_laps = True
        if fast_lap_data:
            current_lap_ids = fast_lap.data["lap_ids"]
            new_lap_ids = data["lap_ids"]
            based_on_new_laps = new_lap_ids != current_lap_ids

        if force_save or got_new_laps or based_on_new_laps:
            fast_lap.data = data
            fast_lap.laps.set(laps)
            fast_lap.save()
            logging.debug("### SAVED ###")
        else:
            logging.debug("!!! NO CHANGE - NOT SAVING !!!")
