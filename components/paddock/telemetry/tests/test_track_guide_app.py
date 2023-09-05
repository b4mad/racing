from pprint import pprint  # noqa

from django.test import TransactionTestCase

from telemetry.models import Coach, Driver
from telemetry.pitcrew.coach_app import CoachApp
from telemetry.pitcrew.history import History

from .utils import get_session_df, read_responses, save_responses  # noqa


class TestTrackGuideApp(TransactionTestCase):
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

    def test_track_guide_iracing(self):
        # iRacing / Mazda MX-5 Cup / okayama short

        session_id = "1690362827"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        coach.mode = Coach.MODE_TRACK_GUIDE_APP
        coach.save()

        history = History()

        coach = CoachApp(history, coach)

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

        expected_responses = read_responses("test_track_guide_app_iracing")
        # save_responses(captured_responses, "test_track_guide_app_iracing")

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
