from django.db import models
import datetime


class Driver(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    name = models.CharField(max_length=200)
    length = models.IntegerField(default=0)

    game = models.ForeignKey(Game, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Car(models.Model):
    name = models.CharField(max_length=200)

    game = models.ForeignKey(Game, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class SessionType(models.Model):
    type = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.type


class Session(models.Model):
    session_id = models.CharField(max_length=200)
    start = models.DateTimeField(default=datetime.datetime.now)
    end = models.DateTimeField(default=datetime.datetime.now)

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    session_type = models.ForeignKey(SessionType, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            "driver",
            "session_id",
            "session_type",
            "game",
            "car",
            "track",
        )

    def __str__(self):
        return self.session_id


class Lap(models.Model):
    number = models.IntegerField()
    start = models.DateTimeField(default=datetime.datetime.now)
    time = models.FloatField(default=0)
    length = models.IntegerField(default=0)

    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("session", "start")


## coach data
class FastLap(models.Model):

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.game} {self.car} {self.track}"


class FastLapSegment(models.Model):
    turn = models.CharField(max_length=200)
    start = models.IntegerField(default=0)
    end = models.IntegerField(default=0)
    brake = models.IntegerField(default=0)
    turn_in = models.IntegerField(default=0)
    force = models.IntegerField(default=0)
    gear = models.IntegerField(default=0)
    stop = models.IntegerField(default=0)
    accelerate = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    mark = models.CharField(max_length=256, default="")

    fast_lap = models.ForeignKey(
        FastLap, related_name="fast_lap_segments", on_delete=models.CASCADE
    )


class Coach(models.Model):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    error = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.driver.name
