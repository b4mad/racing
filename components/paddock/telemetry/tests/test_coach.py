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

            # new session crewchief/durandom/1681897871/iRacing/fuji nochicane/Ferrari 488 GT3 Evo 2020/Practice
            # loading segments for iRacing fuji nochicane - Ferrari 488 GT3 Evo 2020
            # segment 1: 573 - 775 brake: 0 turn_in: 0 force: 79 gear: 2 stop: 0 acc: 0 speed: 17 mark: brake
            # segment 2: 1204 - 1360 brake: 0 turn_in: 0 force: 41 gear: 4 stop: 0 acc: 0 speed: 43 mark: brake
            # segment 3: 1462 - 1807 brake: 0 turn_in: 0 force: 0 gear: 4 stop: 0 acc: 0 speed: 44 mark: throttle
            # segment 4: 1877 - 2027 brake: 0 turn_in: 0 force: 59 gear: 2 stop: 0 acc: 0 speed: 28 mark: brake
            # segment 5: 2676 - 2823 brake: 0 turn_in: 0 force: 73 gear: 4 stop: 0 acc: 0 speed: 37 mark: brake
            # segment 6: 2974 - 3109 brake: 0 turn_in: 0 force: 38 gear: 2 stop: 0 acc: 0 speed: 27 mark: brake
            # segment 7: 3198 - 3374 brake: 0 turn_in: 0 force: 0 gear: 2 stop: 0 acc: 0 speed: 24 mark: throttle
            # segment 8: 3462 - 3638 brake: 0 turn_in: 0 force: 0 gear: 2 stop: 0 acc: 0 speed: 24 mark: throttle
            # loaded 8 segments

        expected_responses = [
            ("/coach/durandom", '{"message": "gear 2 80 percent", "distance": 342, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 573, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 40 percent", "distance": 1025, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1204, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 1250, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 1462, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 60 percent", "distance": 1725, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1877, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 70 percent", "distance": 2474, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2676, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 40 percent", "distance": 2836, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2974, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 3027, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 3198, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 3300, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 3462, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 80 percent", "distance": 342, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 573, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 40 percent", "distance": 1025, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1204, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 1250, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 1462, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 60 percent", "distance": 1725, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 1877, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 4 70 percent", "distance": 2474, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2676, "priority": 9}'),
            ("/coach/durandom", '{"message": "gear 2 40 percent", "distance": 2836, "priority": 9}'),
            ("/coach/durandom", '{"message": "brake", "distance": 2974, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 3027, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 3198, "priority": 9}'),
            ("/coach/durandom", '{"message": "throttle to 0", "distance": 3300, "priority": 9}'),
            ("/coach/durandom", '{"message": "now", "distance": 3462, "priority": 9}'),
        ]

        pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
