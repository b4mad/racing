from django.test import TransactionTestCase
from telemetry.pitcrew.history import History
from telemetry.pitcrew.coach import Coach as PitCrewCoach
from telemetry.models import Driver
from .utils import get_session_df
from pprint import pprint  # noqa


class TestHistory(TransactionTestCase):
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

    def test_distance(self):
        # iRacing fuji nochicane - Ferrari 488 GT3 Evo 2020
        session_id = "1681897871"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        history = History()
        coach = PitCrewCoach(history, coach)
        session_df = get_session_df(session_id, measurement="laps_cc", bucket="racing-smaug")
        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        history.init()

        pprint(history.track_length)

        # pprint(captured_responses, width=200)
        # self.assertEqual(captured_responses, expected_responses)
