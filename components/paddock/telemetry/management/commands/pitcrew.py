import threading

from django.core.management.base import BaseCommand
from flask import Flask
from flask_healthz import healthz

from telemetry.models import Coach, Driver, FastLap
from telemetry.pitcrew.crew import Crew


class Command(BaseCommand):
    help = "start pitcrew"

    def add_arguments(self, parser):
        parser.add_argument("-c", "--coach", nargs="?", type=str, default=None)
        parser.add_argument("-r", "--replay", action="store_true")
        parser.add_argument("-s", "--session-saver", action="store_true")
        parser.add_argument("-n", "--no-save", action="store_true")
        parser.add_argument("-d", "--delete-driver-fastlaps", action="store_true")

    def handle(self, *args, **options):
        if options["delete_driver_fastlaps"]:
            # get all fastlaps where driver is not empty
            FastLap.objects.filter(driver__isnull=False).delete()
            return

        crew = Crew(save=(not options["no_save"]), replay=options["replay"])
        if options["coach"]:
            driver, created = Driver.objects.get_or_create(name=options["coach"])
            coach, created = Coach.objects.get_or_create(driver=driver)
            crew.coach_watcher.start_coach(driver.name, coach, debug=True)
        elif options["session_saver"]:
            t = threading.Thread(target=crew.firehose.run)
            t.name = "firehose"
            t.start()
            t = threading.Thread(target=crew.session_saver.run)
            t.name = "session_saver"
            t.start()
        else:
            if not crew.replay and not options["no_save"]:

                def start_flask():
                    app = Flask(__name__)
                    app.register_blueprint(healthz, url_prefix="/healthz")
                    app.config["HEALTHZ"] = {"live": crew.live, "ready": crew.ready}
                    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

                flask_thread = threading.Thread(target=start_flask)
                flask_thread.start()

            crew.run()
            # TODO: if we end up here, we should probably exit the flask thread
