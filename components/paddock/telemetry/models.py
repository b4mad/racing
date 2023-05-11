from django.db import models
from dirtyfields import DirtyFieldsMixin
from picklefield.fields import PickledObjectField
import datetime


class Driver(models.Model):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200)
    length = models.IntegerField(default=0)

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="tracks")

    def __str__(self):
        return self.name


class Car(models.Model):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200)

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="cars")

    def __str__(self):
        return self.name


class SessionType(models.Model):
    type = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.type


class Session(DirtyFieldsMixin, models.Model):
    session_id = models.CharField(max_length=200)
    start = models.DateTimeField(default=datetime.datetime.now)
    end = models.DateTimeField(default=datetime.datetime.now)

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="sessions")
    session_type = models.ForeignKey(SessionType, on_delete=models.CASCADE, related_name="sessions")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="sessions")

    class Meta:
        unique_together = (
            "driver",
            "session_id",
            "session_type",
            "game",
        )

    def __str__(self):
        return self.session_id


class FastLap(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="fast_laps", null=True)
    # add binary field to hold arbitrary data
    data = PickledObjectField(null=True)

    def __str__(self):
        return f"{self.game} {self.car} {self.track}"


class Lap(DirtyFieldsMixin, models.Model):
    number = models.IntegerField()
    start = models.DateTimeField(default=datetime.datetime.now)
    end = models.DateTimeField(default=datetime.datetime.now)
    time = models.FloatField(default=0)
    length = models.IntegerField(default=0)
    valid = models.BooleanField(default=False)

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="laps")
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="laps")
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="laps")
    fast_lap = models.ForeignKey(FastLap, on_delete=models.CASCADE, related_name="laps", null=True)

    class Meta:
        ordering = [
            "number",
        ]
        unique_together = ("session", "start")

    def __str__(self):
        return (
            f"{self.number}: {self.start.strftime('%H:%M:%S')} - {self.end.strftime('%H:%M:%S')} "
            + f"{self.time}s {self.length}m valid: {self.valid}"
        )


class FastLapSegment(models.Model):
    turn = models.CharField(max_length=200)
    start = models.IntegerField(default=0)
    end = models.IntegerField(default=0)
    brake = models.IntegerField(default=0)
    turn_in = models.IntegerField(default=0)
    force = models.IntegerField(default=0)
    gear = models.IntegerField(default=0)
    # stop is the time the brake force starts to decrease
    stop = models.IntegerField(default=0)
    accelerate = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    mark = models.CharField(max_length=256, default="")

    fast_lap = models.ForeignKey(FastLap, on_delete=models.CASCADE, related_name="fast_lap_segments")

    def __str__(self):
        repr = f"{self.turn}: {self.start} - {self.end} brake: {self.brake} "
        repr += f"turn_in: {self.turn_in} force: {self.force} gear: {self.gear} stop: {self.stop} "
        repr += f"acc: {self.accelerate} speed: {self.speed} mark: {self.mark}"
        return repr


class Coach(models.Model):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    error = models.TextField(default="")
    status = models.TextField(default="")
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.driver.name
