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
        "fastlap.json",
        "fastlapsegment.json",
        "driver.json",
        "coach.json",
    ]
    maxDiff = None

    def test_message_stack(self):
        # create messages to add to stack
        message1 = {"at": 10, "text": "Message 1"}
        message2 = {"at": 20, "text": "Message 2"}
        message3 = {"at": 30, "text": "Message 3"}
        message4 = {"at": 40, "text": "Message 4"}
        messages = [message4, message1, message3, message2]

        history = History()
        coach = PitCrewCoach(history, Driver.objects.get(name="durandom").coach)

        # set messages for the stack
        coach.messages = messages

        # get message stack for distance of 12
        message_stack = coach.sort_messages(12)

        expected_messages = [message2, message3, message4, message1]
        # assert expected message stack matches the actual message stack
        self.assertEqual(expected_messages, message_stack)

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
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1009, "message": "gear 4 40 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1208.94, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2457, "message": "gear 4 70 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2680.99, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2823, "message": "gear 2 30 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2979.0, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3085, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3238.01, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3353, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3497.02, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 326, "message": "gear 2 80 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1009, "message": "gear 4 40 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1208.94, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2457, "message": "gear 4 70 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2680.99, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3085, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3238.01, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1009, "message": "gear 4 40 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1208.94, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 326, "message": "gear 2 80 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2823, "message": "gear 2 30 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2979.0, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3085, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3238.01, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 326, "message": "gear 2 80 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2823, "message": "gear 2 30 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2979.0, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3085, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3238.01, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2823, "message": "gear 2 30 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2979.0, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3353, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3497.02, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 326, "message": "gear 2 80 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1715, "message": "gear 2 60 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1881.96, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2457, "message": "gear 4 70 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2680.99, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 326, "message": "gear 2 80 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 577.91, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1340, "message": "throttle to 0", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1461.95, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1664, "message": "throttle to 80", "priority": 9}'),
            ("/coach/durandom", '{"distance": 1783.96, "message": "now", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2457, "message": "gear 4 70 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2680.99, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2823, "message": "gear 2 30 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 2979.0, "message": "brake", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3353, "message": "gear 2 20 percent", "priority": 9}'),
            ("/coach/durandom", '{"distance": 3497.02, "message": "brake", "priority": 9}'),
        ]

        pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
