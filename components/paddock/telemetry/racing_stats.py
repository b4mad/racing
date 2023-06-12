from telemetry.models import Game, Track, Lap, FastLap
from django.db import connection
from django.db.models import Count


class RacingStats:
    def __init__(self):
        pass

    def known_combos_list(self, game=None, track=None, car=None, **kwargs):
        laps = self.known_combos(game, track, car, **kwargs)
        for row in laps:
            yield row["track__game__name"], row["car__name"], row["track__name"], row["count"]

    def known_combos(self, game=None, track=None, car=None, **kwargs):
        filter = {}
        if game:
            filter["track__game__name"] = game
        if track:
            filter["track__name"] = track
        if car:
            filter["car__name"] = car

        filter["valid"] = True
        laps = Lap.objects.filter(**filter)
        # group by track and car and game
        laps = laps.values("track__name", "car__name", "track__game__name")
        laps = laps.annotate(count=Count("id"))
        laps = laps.order_by("track__game__name", "car__name", "track__name")
        return laps

    def fast_lap_values(self, game=None, track=None, car=None, **kwargs):
        filter = {}
        if game:
            filter["game__name"] = game
        if track:
            filter["track__name"] = track
        if car:
            filter["car__name"] = car

        filter["driver"] = None

        laps = FastLap.objects.filter(**filter)
        # group by track and car and game
        laps = laps.values("track__name", "car__name", "game__name")
        # laps = laps.annotate(count=Count("id"))
        laps = laps.order_by("game__name", "car__name", "track__name")
        return laps
        # for row in laps:
        #     yield row["track__game__name"], row["car__name"], row["track__name"], row["count"]

    def fast_laps(self, game=None, track=None, car=None, **kwargs):
        filter = {}
        filter["game__name"] = game
        filter["track__name"] = track
        filter["car__name"] = car

        laps = FastLap.objects.filter(**filter)
        return laps

    def laps(self, game=None, track=None, car=None, valid=None, **kwargs):
        filter = {}
        if game:
            filter["track__game__name"] = game
        if track:
            filter["track__name"] = track
        if car:
            filter["car__name"] = car

        if valid is not None:
            filter["valid"] = valid

        laps = Lap.objects.filter(**filter)
        laps = laps.order_by("time")
        # limit to 10
        # laps = laps[:10]
        return laps

        # for lap in laps:
        #     yield lap

    def fast_laps_cursor(self, game=None, track=None, car=None, **kwargs):
        where = []
        filter_game = None
        if game:
            filter_game = Game.objects.get(name=game)
        if track:
            track = Track.objects.get(name=track)
            where.append(f" track_id={track.pk}")
        if car:
            # get the first car with this name
            car = filter_game.cars.filter(name=car).first()
            where.append(f"car_id={car.pk}")

        where_clause = ""
        if where:
            where_clause = "where " + " and ".join(where)

        sql = f"select count(id) as c, track_id, car_id from telemetry_lap {where_clause} group by track_id, car_id"

        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        return rows
