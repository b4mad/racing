from pprint import pprint  # noqa

from django.test import TransactionTestCase

from telemetry.models import Coach, Driver, TrackGuide
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

    do_save_responses = True

    def test_no_trackguide(self):
        # iRacing / Mazda MX-5 Cup / okayama short

        session_id = "1690362827"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        coach.mode = Coach.MODE_TRACK_GUIDE_APP
        coach.save()

        # delete the trackguide
        TrackGuide.objects.get(track__name="okayama short", car__name="Mazda MX-5 Cup").delete()

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

        responses_file = "test_track_guide_app_no_trackguide"
        expected_responses = read_responses(responses_file)
        if self.do_save_responses:
            save_responses(captured_responses, responses_file)

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)

    def test_no_data_found(self):
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
        topic = row["topic"].replace("Mazda MX-5 Cup", "Ferrari 488 GT3 Evo 2020")
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

        responses_file = "test_track_guide_app_no_data_found"
        expected_responses = read_responses(responses_file)
        if self.do_save_responses:
            save_responses(captured_responses, responses_file)

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)

    def test_track_guide_iracing(self):
        # iRacing / Mazda MX-5 Cup / okayama short

        # session by durandom
        # first 2 laps are slow
        # 3rd lap has a spin in the first turn
        # reset to pits
        # fast out of pits
        # spin at turn 2
        # continue at fast pace for one more lap
        # then slow down after finish line
        session_id = "1694266648"
        driver = Driver.objects.get(name="durandom")
        coach = driver.coach
        coach.mode = Coach.MODE_TRACK_GUIDE_APP
        coach.save()

        history = History()

        coach = CoachApp(history, coach)

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
                    distance_response = (row["DistanceRoundTrack"], response)
                    history.log_debug(distance_response)
                    captured_responses.append(distance_response)
        except Exception as e:
            raise e
        finally:
            print("stopping history thread")
            history.disconnect()

        responses_file = "test_track_guide_app_iracing"
        expected_responses = read_responses(responses_file)
        if self.do_save_responses:
            save_responses(captured_responses, responses_file)

        # pprint(captured_responses, width=200)
        self.assertEqual(captured_responses, expected_responses)
