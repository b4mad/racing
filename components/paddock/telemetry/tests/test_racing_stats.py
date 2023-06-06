from django.test import TransactionTestCase
from telemetry.racing_stats import RacingStats


class TestRacingStats(TransactionTestCase):
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

    def test_stats(self):
        racing_stats = RacingStats()

        self.assertEqual(racing_stats.laps().count(), 2)
