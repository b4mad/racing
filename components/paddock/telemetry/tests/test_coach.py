from django.test import TransactionTestCase
import threading
from telemetry.pitcrew.coach import Coach as PitCrewCoach
from telemetry.pitcrew.history import History
from telemetry.models import Driver
import time
from .utils import get_session_df


class TestCoach(TransactionTestCase):
    fixtures = [
        "game.json",
        "track.json",
        "car.json",
        "fastlap.json",
        "fastlapsegment.json",
        "driver.json",
        "coach.json",
    ]

    def test_coach(self):
        session_id = "1681897871"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach

        history = History()
        threading.Thread(target=history.run).start()

        coach = PitCrewCoach(history, coach)

        session_df = get_session_df(session_id, measurement="laps_cc", bucket="racing-smaug")

        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        print("waiting for history to be ready")
        while not history.ready:
            time.sleep(0.1)

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

        expected_responses = [
            ("/coach/durandom", '{"message": "brake", "distance": 586, "priority": 9}'),
            ("/coach/durandom", "gear 4 90 percent"),
            ("/coach/durandom", '{"message": "brake", "distance": 1198, "priority": 9}'),
            ("/coach/durandom", "throttle to 0"),
            ("/coach/durandom", '{"message": "now", "distance": 1497, "priority": 9}'),
            ("/coach/durandom", "gear 2 100 percent"),
            ("/coach/durandom", '{"message": "brake", "distance": 1889, "priority": 9}'),
            ("/coach/durandom", "gear 3 100 percent"),
            ("/coach/durandom", '{"message": "brake", "distance": 2688, "priority": 9}'),
            ("/coach/durandom", "gear 2 100 percent"),
            ("/coach/durandom", '{"message": "brake", "distance": 2981, "priority": 9}'),
            ("/coach/durandom", "gear 2 70 percent"),
            ("/coach/durandom", '{"message": "brake", "distance": 3500, "priority": 9}'),
            ("/coach/durandom", "gear 1 100 percent"),
        ]
        self.assertEqual(captured_responses, expected_responses)
