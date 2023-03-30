import datetime
from django.core.management.base import BaseCommand
from telemetry.influx import Influx
import logging


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

    def handle(self, *args, **options):
        influx = Influx()
        if options["delete_influx"]:
            if options["start"]:
                start = datetime.datetime.strptime(options["start"], "%Y-%m-%d")
            else:
                start = datetime.datetime.now() - datetime.timedelta(days=30)

            if options["end"]:
                end = datetime.datetime.strptime(options["end"], "%Y-%m-%d")
            else:
                end = start + datetime.timedelta(days=1)

            # delete in on hour chunks
            while start < end:
                end_delta = start + datetime.timedelta(hours=4)
                logging.debug(f"Deleting data from {start} to {end_delta}")
                now = datetime.datetime.now()
                influx.delete_data(start=start, end=end_delta)
                # log how long it took
                logging.debug(f"... {datetime.datetime.now() - now}")
                start = end_delta
