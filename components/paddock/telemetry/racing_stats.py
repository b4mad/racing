from datetime import datetime, timedelta

from django.db import connection
from django.db.models import CharField, Count, Max, Q, Value

from telemetry.models import FastLap, Game, Lap, Track


class RacingStats:
    def __init__(self):
        pass

    def combos(self, type="", **kwargs):
        return self.driver_combos(type=type, **kwargs)

    def driver_combos(self, driver=None, range=30, type="circuit", **kwargs):
        filter = {}
        if driver is not None:
            filter["session__driver__name"] = driver

        # Calculate the start date based on the range
        start_date = datetime.now() - timedelta(days=range)

        laps = Lap.objects.filter(**filter)
        # Filter laps based on the end time within the range
        laps = laps.filter(session__end__gte=start_date)
        # group by game, track, and car
        if type == "circuit" or type == "":
            laps = laps.values(
                "session__game__name", "track__name", "car__name", "session__game__id", "track__id", "car__id"
            )
            # annotate with count of laps, valid laps, and latest lap end time
            laps = laps.annotate(
                lap_count=Count("id"), valid_lap_count=Count("id", filter=Q(valid=True)), latest_lap_end=Max("end")
            )
            if type == "circuit":
                # exclude all rally games: Richard Burns Rally, Dirt Rally, Dirt Rally 2.0
                laps = laps.exclude(session__game__name__in=["Richard Burns Rally", "Dirt Rally", "Dirt Rally 2.0"])
        elif type == "rally":
            laps = laps.values("session__game__name", "car__name", "session__game__id", "car__id", "track__game__id")
            # add a field called track__name with a hardcoded value of "Multiple"
            laps = laps.annotate(
                track__name=Value("Multiple", output_field=CharField()),
                track__id=Value(0, output_field=CharField()),
                lap_count=Count("id"),
                valid_lap_count=Count("id", filter=Q(valid=True)),
                latest_lap_end=Max("end"),
            )
            # only include rally games: Richard Burns Rally, Dirt Rally, Dirt Rally 2.0
            laps = laps.filter(session__game__name__in=["Richard Burns Rally", "Dirt Rally", "Dirt Rally 2.0"])
        # order by latest lap end time
        laps = laps.order_by("-latest_lap_end")

        # show the sql of the query
        # print(laps.query)

        return laps

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

    def laps(self, game=None, track=None, car=None, driver=None, valid=None, **kwargs):
        filter = {}
        if game:
            filter["track__game__name"] = game
        if track:
            filter["track__name"] = track
        if car:
            filter["car__name"] = car

        if valid is not None:
            filter["valid"] = valid

        if driver is not None:
            filter["session__driver__name"] = driver

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
