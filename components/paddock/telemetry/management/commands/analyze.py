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

            used_laps = self.analyze_fast_laps(valid_laps, min_laps=min_laps, max_laps=max_laps)

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

    def analyze_fast_laps(self, fast_laps, min_laps=1, max_laps=10):
        fl = FastLapAnalyzer(fast_laps)
        result = fl.analyze(min_laps=min_laps, max_laps=max_laps)
        if result:
            data = result[0]
            used_laps = result[1]
            logging.debug(f"found {len(data['segments'])} sectors in {len(used_laps)} laps")
            self.save_fastlap(data, laps=used_laps)
            return used_laps
        else:
            logging.error("no result")

    def save_fastlap(self, data, laps=[]):
        if not laps:
            logging.error("no laps")
            return
        lap = laps[0]
        car = lap.car
        track = lap.track
        game = lap.session.game
        fast_lap, created = FastLap.objects.get_or_create(car=car, track=track, game=game, driver=None)
        fast_lap.data = data
        fast_lap.laps.set(laps)
        fast_lap.save()
        # print(data['segments'][0].telemetry)
        # fast_lap.fast_lap_segments.all().delete()
        # i = 1
        # for s in track_info:
        #     s["turn"] = i
        #     fast_lap.fast_lap_segments.create(
        #         turn=i,
        #         mark=s["mark"],
        #         start=s["start"],
        #         end=s["end"],
        #         force=s["force"],
        #         gear=s["gear"],
        #         speed=s["speed"],
        #     )
        #     i += 1
        # also delete user segments
        # FIXME only delete user segements if they changed?
        # r = FastLap.objects.filter(car=car, track=track, game=game).exclude(driver=None).delete()
        # logging.debug(f"deleted {r} user segments")
