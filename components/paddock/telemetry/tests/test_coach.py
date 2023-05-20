from django.test import TransactionTestCase
import threading
from telemetry.pitcrew.coach import Coach as PitCrewCoach
from telemetry.pitcrew.history import History
from telemetry.models import Driver
import time
from .utils import get_session_df
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

        expected_responses = [
            ("/coach/durandom", "start coaching for a lap time of 1 minute 37.01 seconds "),
            ("/coach/durandom", ['{"distance": 969, "message": "Gear 4 40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1208, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle to 0 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1461, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "Gear 2 60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1783, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1881, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2680, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2979, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "Gear 2 20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3238, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "Gear 2 20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3497, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 577, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 969, "message": "Gear 4 40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1208, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift a bit earlier", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1461, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3238, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1461, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1881, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle to 0 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1783, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3238, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "Gear 4 40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1461, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2979, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1461, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle to 0 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 269, "message": "Gear 2 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 969, "message": "40 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1265, "message": "lift throttle to 0 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1583, "message": "lift throttle to 80 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1678, "message": "60 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 1783, "message": "lift", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 2410, "message": "Gear 4 70 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 2793, "message": "Gear 2 30 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "Gear 2 20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3497, "message": "brake", "priority": 8}']),
            ("/coach/durandom", ['{"distance": 3063, "message": "20 percent", "priority": 9}']),
            ("/coach/durandom", ['{"distance": 3333, "message": "20 percent", "priority": 9}']),
        ]

        pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
