import datetime
import logging

from django.core.management.base import BaseCommand

from telemetry.influx import Influx
from telemetry.models import Session


class Command(BaseCommand):
    help = "clean stuff"

    def add_arguments(self, parser):
        # add argument for list of lap ids as integers separated by commas
        parser.add_argument(
            "-d",
            "--delete-influx",
            help="delete old influx data",
            action="store_true",
        )

        parser.add_argument(
            "--delete-sessions",
            help="delete sessions",
            action="store_true",
        )

        parser.add_argument(
            "-s",
            "--start",
            help="start date for deletion",
            type=str,
            default=None,
        )
        parser.add_argument(
            "-e",
            "--end",
            help="end date for deletion",
            type=str,
            default=None,
        )

        parser.add_argument(
            "--fix-rbr-sessions",
            help="fix data",
            action="store_true",
        )

    def handle(self, *args, **options):
        self.influx = Influx()
        if options["delete_influx"]:
            self.delete_influx(options["start"], options["end"])
        elif options["delete_sessions"]:
            self.delete_sessions(options["start"], options["end"])
        elif options["fix_rbr_sessions"]:
            self.fix_rbr_sessions()

    def fix_rbr_sessions(self):
        # get all sessions for Richard Burns Rally
        sessions = Session.objects.filter(game__name="Richard Burns Rally")
        for session in sessions:
            # get all laps for this session
            laps = session.laps.all()
            # iterate over all laps
            for lap in laps:
                print(f"fixing lap {lap.id} end: {lap.end}")
                # set the end time of the lap to the start + the lap time
                lap.end = lap.start + datetime.timedelta(seconds=lap.time + 60)
                print(f"--> {lap.end}")
                lap.number = 0
                # save the lap
                lap.save()

    def delete_sessions(self, start, end):
        Session.objects.all().delete()

    def delete_influx(self, start, end):
        if start:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")
        else:
            start = datetime.datetime.now() - datetime.timedelta(days=30)

        if end:
            end = datetime.datetime.strptime(end, "%Y-%m-%d")
        else:
            end = start + datetime.timedelta(days=1)

        # delete in on hour chunks
        while start < end:
            end_delta = start + datetime.timedelta(hours=4)
            logging.debug(f"Deleting data from {start} to {end_delta}")
            now = datetime.datetime.now()
            self.influx.delete_data(start=start, end=end_delta)
            # log how long it took
            logging.debug(f"... {datetime.datetime.now() - now}")
            start = end_delta
