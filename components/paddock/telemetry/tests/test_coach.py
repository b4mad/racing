from django.test import TransactionTestCase
import threading
from telemetry.pitcrew.coach import Coach as PitCrewCoach
from telemetry.pitcrew.history import History
from telemetry.models import Driver
import time
from .utils import get_session_df, read_responses, save_responses  # noqa
from pprint import pprint  # noqa


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
            while not history.ready:
                time.sleep(0.1)
        else:
            history.init()

        captured_responses = []
        try:
            for index, row in session_df.iterrows():
                row = row.to_dict()
                response = coach.notify(topic, row)
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
