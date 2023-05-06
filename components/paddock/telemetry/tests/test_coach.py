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

    def _assert_laps(self, test_session, expected_laps):
        # Iterate over the expected_laps dictionary and compare to the test_session.laps
        for lap_number, expected_lap in expected_laps.items():
            lap = test_session.laps[lap_number]

            self.assertEqual(lap.number, expected_lap.number)
            self.assertEqual(lap.time, expected_lap.time)
            self.assertEqual(lap.valid, expected_lap.valid)
            self.assertEqual(lap.finished, expected_lap.finished)
            self.assertAlmostEqual(int(lap.length), int(expected_lap.length), places=0)

            if lap.time != -1:
                # the difference between lap.end and lap.start should be equal to lap.time
                time_delta = lap.end - lap.start
                self.assertAlmostEqual(
                    time_delta.total_seconds(), expected_lap.time, places=0
                )

    def test_coach(self):
        session_id = "1681897871"
        # game = Game.objects.get(name="iRacing")
        # track = Track.objects.get(name="fuji nochicane")
        # car = Car.objects.get(name="Ferrari 488 GT3 Evo 2020")
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach

        history = History()
        threading.Thread(target=history.run).start()

        coach = PitCrewCoach(history, coach)

        session_df = get_session_df(
            session_id, measurement="laps_cc", bucket="racing-smaug"
        )

        row = session_df.iloc[0].to_dict()
        topic = row["topic"].replace("Jim", "durandom")
        coach.notify(topic, row)
        print("waiting for history to be ready")
        while not history.ready:
            time.sleep(0.1)

        for index, row in session_df.iterrows():
            # convert row to dict
            row = row.to_dict()
            # now = row["_time"]
            response = coach.notify(topic, row)
            if response:
                print(response)

        history.disconnect()


# Loading .env environment variables...
# 2023-05-05 21:34:54,954 DEBUG Influx: Connected to http://telemetry.b4mad.racing/
# 2023-05-05 21:34:55,052 INFO 62 laps for iRacing / fuji nochicane / Ferrari 488 GT3 Evo 2020
# 2023-05-05 21:34:55,057 DEBUG median time: 99.8834, median length: 4459.0
# 2023-05-05 21:34:55,072 DEBUG 5: 12:00:13 - 12:01:51 98.1661s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 1: 16:42:11 - 16:43:49 98.3445s 4458m valid: True
# 2023-05-05 21:34:55,073 DEBUG 2: 15:52:50 - 15:54:28 98.3852s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 5: 11:18:54 - 11:20:33 98.6412s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 6: 12:01:51 - 12:03:30 98.6557s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 2: 11:54:54 - 11:56:33 98.7071s 4458m valid: True
# 2023-05-05 21:34:55,073 DEBUG 4: 11:17:15 - 11:18:54 98.8119s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 4: 10:05:33 - 10:07:11 98.8916s 4459m valid: True
# 2023-05-05 21:34:55,073 DEBUG 3: 10:03:54 - 10:05:33 98.9114s 4459m valid: True
# 2023-05-05 21:34:55,092 DEBUG Influx: Connected to http://telemetry.b4mad.racing/
# 2023-05-05 21:34:55,105 INFO Processing iRacing fuji nochicane :
#    session 1681827784 : lap.id 12752 : length 4459 : time 97.924
# 2023-05-05 21:34:56,086 DEBUG CONFIGDIR=/Users/mhild/.matplotlib
# 2023-05-05 21:34:56,087 DEBUG interactive is False
# 2023-05-05 21:34:56,087 DEBUG platform is darwin
# 2023-05-05 21:34:56,114 DEBUG CACHEDIR=/Users/mhild/.matplotlib
# 2023-05-05 21:34:56,239 INFO  mark start end gear force speed
# 0 brake 586 812 1.0 99.0 20.3
# 1 brake 1198 1312 4.0 91.0 42.8
# 2 throttle 1497 1756 4.0 1.0 44.3
# 3 brake 1889 2045 2.0 97.0 23.5
# 4 brake 2688 2820 3.0 99.0 33.9
# 5 brake 2981 3380 2.0 96.0 22.6
# 6 brake 3500 3653 2.0 73.0 23.5

# {'mark': 'brake', 'start': 586, 'end': 812, 'gear': 1.0, 'force': 99.0, 'speed': 20.338105506337655, 'turn': 1}
# {'mark': 'brake', 'start': 1198, 'end': 1312, 'gear': 4.0, 'force': 91.0, 'speed': 42.826536270099425, 'turn': 2}
# {'mark': 'throttle', 'start': 1497, 'end': 1756, 'gear': 4.0, 'force': 1.0, 'speed': 44.346462285338774, 'turn': 3}
# {'mark': 'brake', 'start': 1889, 'end': 2045, 'gear': 2.0, 'force': 97.0, 'speed': 23.530448482807955, 'turn': 4}
# {'mark': 'brake', 'start': 2688, 'end': 2820, 'gear': 3.0, 'force': 99.0, 'speed': 33.88839617473414, 'turn': 5}
# {'mark': 'brake', 'start': 2981, 'end': 3380, 'gear': 2.0, 'force': 96.0, 'speed': 22.643702570011325, 'turn': 6}
# {'mark': 'brake', 'start': 3500, 'end': 3653, 'gear': 2.0, 'force': 73.0, 'speed': 23.47308603076716, 'turn': 7}
# 2023-05-05 21:34:56,362 DEBUG deleted (0, {}) user segments
