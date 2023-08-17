from pprint import pprint

import django.utils.timezone
from django.db import IntegrityError
from django.test import TestCase

from telemetry.models import Car, Driver, Game
from telemetry.models import Session as SessionModel
from telemetry.models import SessionType, Track
from telemetry.pitcrew.session import Lap, Session

from .utils import get_session_df


class TestSession(TestCase):
    def _test_session(self, session_id, measurement="fast_laps", bucket="fast_laps"):
        session_df = get_session_df(session_id, measurement=measurement, bucket=bucket)

        # Create an instance of the Session class
        test_session = Session(666)

        for index, row in session_df.iterrows():
            # convert row to dict
            row = row.to_dict()
            now = row["_time"]
            test_session.signal(row, now)

        pprint(test_session.laps)
        return test_session

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
                self.assertAlmostEqual(time_delta.total_seconds(), expected_lap.time, places=0)

    def test_iracing(self):
        # measurement = "fast_laps"
        # bucket = "fast_laps"
        # start = "-10y"
        session_id = "1681021274"

        # For this session the following laps are valid:
        # 1 valid: during outlap lap_number is 1, remains 1 on crossing finish line
        # 2 invalid: penalty during lap, reset to pits, lap_number is remains 2 on outlap
        # 3 valid: lap_number changes to 3 on crossing finish line
        # 4 valid: lap_number changes to 4 on crossing finish line
        # 5 valid: lap_number changes to 5 on crossing finish line
        # 6 invalid: penalty during lap, no reset to pits
        # 7 invalid: lap_number changes to 7 on crossing finish line,
        #            no penalty during lap, but "PreviousLapWasValid" is false
        # 8 invalid: penalty during lap, reset to pits, lap_number is remains 8 on outlap
        # 9 invalid: penalty during lap, no reset to pits
        # 10 invalid: penalty during lap, eset to pits
        # a lap time of -1 indicates an outlap

        expected_laps = {
            1: Lap(1, time=100.818, valid=True, length=4409),
            2: Lap(2, time=-1, valid=False, length=4408),
            3: Lap(3, time=101.0466, valid=True, length=4408),
            4: Lap(4, time=100.823, valid=True, length=4408),
            5: Lap(5, time=99.4026, valid=True, length=4410),
            6: Lap(6, time=107.9166, valid=False, length=4410),
            7: Lap(7, time=99.0674, valid=False, length=4410),
            8: Lap(8, time=-1, valid=False, length=4409),
            9: Lap(9, time=101.7361, valid=False, length=4409),
            10: Lap(10, time=-1, valid=False, length=1890),
        }
        for lap_number, expected_lap in expected_laps.items():
            expected_lap.finished = True
        expected_laps[10].finished = False
        session = self._test_session(session_id)
        self._assert_laps(session, expected_laps)

    def test_ac(self):
        # measurement = "fast_laps"
        # bucket = "fast_laps"
        # start = "-10y"
        session_id = "1673613558"

        # For this session the following laps are valid:
        expected_laps = {
            2: Lap(2, time=63.79, valid=False, length=2338.449),
            3: Lap(3, time=62.4660034, valid=True, length=2341.24487),
            4: Lap(4, time=64.097, valid=False, length=2339.07666),
            5: Lap(5, time=61.833, valid=True, length=2340.87329),
            6: Lap(6, time=70.983, valid=False, length=2342.41357),
            7: Lap(7, time=61.465, valid=True, length=2337.27051),
            8: Lap(8, time=67.749, valid=True, length=2337.886),
            9: Lap(9, time=61.703, valid=True, length=2338.9856),
            10: Lap(10, time=73.402, valid=False, length=2341.15625),
            11: Lap(11, time=85.821, valid=False, length=2340.723),
            # 12: Lap(12, time=169.38, valid=False, length=2338.358),  # during this lap the game was paused
            # 12: Lap(12, time=174.319331, valid=False, length=2338.358),
            13: Lap(13, time=64.435, valid=False, length=2337.65625),
            14: Lap(14, time=62.7619972, valid=False, length=2341.5625),
            15: Lap(15, time=77.178, valid=False, length=2341.84863),
            16: Lap(16, time=79.708, valid=False, length=2342.23486),
            17: Lap(17, time=-1.0, valid=True, length=33.61092),
        }
        for lap_number, expected_lap in expected_laps.items():
            expected_lap.finished = True
        expected_laps[17].finished = False

        session = self._test_session(session_id)
        self._assert_laps(session, expected_laps)

    def test_car_class(self):
        session_id = "1692140843"

        session = self._test_session(session_id)

        self.assertEqual(session.car_class, "ARC_CAMERO")

    def test_telemetry_invalid(self):
        # 2390.0: LapTimePrevious: None -> None
        # 2390.0: CurrentLapIsValid: None -> None
        # 2390.0: PreviousLapWasValid: None -> None
        # these values are always None in that session
        session_id = "1672395579"
        session = self._test_session(session_id)
        self.assertEqual(session.laps, {})

    def test_telemetry_missing_fields(self):
        # last lap CurrentLapIsValid is None
        session_id = "1680321341"
        session = self._test_session(session_id)

        expected_laps = {
            11: Lap(11, time=-1, length=82, valid=True, finished=False),
        }
        self._assert_laps(session, expected_laps)

    def test_duplicate_lap(self):
        # create 2 laps with the same number
        game = Game.objects.create(name="test_game")
        track = Track.objects.create(name="test_track", game=game)
        car = Car.objects.create(name="test_car", game=game)
        driver = Driver.objects.create(name="test_driver")
        session_type = SessionType.objects.create(type="test_session_type")
        session = SessionModel.objects.create(session_id=666, driver=driver, game=game, session_type=session_type)

        now = django.utils.timezone.now()

        session.laps.create(number=1, car=car, track=track, start=now)
        try:
            session.laps.create(number=2, car=car, track=track, start=now)
        except IntegrityError as e:
            self.assertEqual(
                e.args[0],
                "UNIQUE constraint failed: telemetry_lap.session_id, telemetry_lap.start",
            )
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")
