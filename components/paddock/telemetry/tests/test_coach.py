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

        # loading segments for iRacing fuji nochicane - Ferrari 488 GT3 Evo 2020
        # segment 1: 586 - 812 brake: 0 turn_in: 0 force: 99 gear: 1 stop: 0 acc: 0 speed: 20 mark: brake
        # segment 2: 1198 - 1312 brake: 0 turn_in: 0 force: 91 gear: 4 stop: 0 acc: 0 speed: 42 mark: brake
        # segment 3: 1497 - 1756 brake: 0 turn_in: 0 force: 1 gear: 4 stop: 0 acc: 0 speed: 44 mark: throttle
        # segment 4: 1889 - 2045 brake: 0 turn_in: 0 force: 97 gear: 2 stop: 0 acc: 0 speed: 23 mark: brake
        # segment 5: 2688 - 2820 brake: 0 turn_in: 0 force: 99 gear: 3 stop: 0 acc: 0 speed: 33 mark: brake
        # segment 6: 2981 - 3380 brake: 0 turn_in: 0 force: 96 gear: 2 stop: 0 acc: 0 speed: 22 mark: brake
        # segment 7: 3500 - 3653 brake: 0 turn_in: 0 force: 73 gear: 2 stop: 0 acc: 0 speed: 23 mark: brake

        expected_responses = [
            ("/coach/durandom", '{"message": "gear 1 100 percent", "distance": 357, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 586, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 90 percent", "distance": 1019, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1198, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 1287, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 1497, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 100 percent", "distance": 1737, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1889, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 3 100 percent", "distance": 2484, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2688, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 100 percent", "distance": 2844, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2981, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 70 percent", "distance": 3384, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 3500, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 1 100 percent", "distance": 357, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 586, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 90 percent", "distance": 1019, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1198, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 1287, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 1497, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 100 percent", "distance": 1737, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1889, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 3 100 percent", "distance": 2484, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2688, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 100 percent", "distance": 2844, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2981, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 70 percent", "distance": 3384, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 3500, "priority": 9}'),
        ]

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
