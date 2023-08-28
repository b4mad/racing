import threading
import time
from pprint import pprint  # noqa

from django.test import TransactionTestCase

from telemetry.models import Coach, Driver
from telemetry.pitcrew.coach import Coach as PitCrewCoach
from telemetry.pitcrew.history import History

from .utils import get_session_df, read_responses, save_responses  # noqa


class TestCoach(TransactionTestCase):
    fixtures = [
        "game.json",
        "track.json",
        "car.json",
        "session.json",
        "sessiontype.json",
        "lap.json",
        "fastlap.json",
        "fastlapsegment.json",
        "driver.json",
        "coach.json",
        "trackguide.json",
        "trackguidenote.json",
        "landmark.json",
    ]
    maxDiff = None

    def test_coach(self):
        # iRacing fuji nochicane - Ferrari 488 GT3 Evo 2020
        session_id = "1681897871"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach

        history = History()

        use_threads = False
        if use_threads:
            threading.Thread(target=history.run).start()

        coach = PitCrewCoach(history, coach)

        session_df = get_session_df(session_id, measurement="laps_cc", bucket="racing-smaug")

        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        if use_threads:
            print("waiting for history to be ready")
            while not history._ready:
                time.sleep(0.1)
        else:
            history.init()
            history._do_init = False

        # get the fast lap for the driver
        fast_lap = driver.fast_laps.get(game=history.game, track=history.track, car=history.car)
        driver_segments = fast_lap.data
        self.assertIsNone(driver_segments)

        captured_responses = []
        try:
            for index, row in session_df.iterrows():
                row = row.to_dict()
                response = coach.notify(topic, row, row["_time"])
                if response:
                    captured_responses.append(response)
        except Exception as e:
            raise e
        finally:
            print("stopping history thread")
            history.disconnect()

        expected_responses = read_responses("test_coach")
        # save_responses(captured_responses, "test_coach")

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)

        # get the fast lap for the driver
        fast_lap.refresh_from_db()
        driver_segments = fast_lap.data["segments"]
        self.assertEqual(len(driver_segments), 8)
        self.assertEqual(len(driver_segments[1].live_features["brake"]), 16)

    def test_track_guide(self):
        # Automobilista 2 / BMW M4 GT4/  Monza:Monza_2020

        session_id = "1692949947"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        coach.mode = Coach.MODE_TRACK_GUIDE
        coach.save()

        history = History()

        coach = PitCrewCoach(history, coach)

        session_df = get_session_df(session_id, measurement="laps_cc", bucket="racing")

        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        history.init()
        history._do_init = False

        captured_responses = []
        try:
            for index, row in session_df.iterrows():
                row = row.to_dict()
                response = coach.notify(topic, row, row["_time"])
                if response:
                    captured_responses.append(response)
        except Exception as e:
            raise e
        finally:
            print("stopping history thread")
            history.disconnect()

        expected_responses = read_responses("test_track_guide")
        # save_responses(captured_responses, "test_track_guide")

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)

    def test_track_guide_iracing(self):
        # iRacing / Mazda MX-5 Cup / okayama short

        session_id = "1690362827"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        coach.mode = Coach.MODE_TRACK_GUIDE
        coach.save()

        history = History()

        coach = PitCrewCoach(history, coach)

        session_df = get_session_df(session_id, measurement="fast_laps", bucket="fast_laps")

        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        history.init()
        history._do_init = False

        captured_responses = []
        try:
            for index, row in session_df.iterrows():
                row = row.to_dict()
                response = coach.notify(topic, row, row["_time"])
                if response:
                    captured_responses.append(response)
        except Exception as e:
            raise e
        finally:
            print("stopping history thread")
            history.disconnect()

        expected_responses = read_responses("test_track_guide_iracing")
        save_responses(captured_responses, "test_track_guide_iracing")

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
