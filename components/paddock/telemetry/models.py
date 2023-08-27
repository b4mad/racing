import datetime

from dirtyfields import DirtyFieldsMixin
from django.db import models
from django_prometheus.models import ExportModelOperationsMixin
from model_utils.models import TimeStampedModel
from picklefield.fields import PickledObjectField


class Driver(ExportModelOperationsMixin("driver"), TimeStampedModel):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Game(TimeStampedModel):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Track(TimeStampedModel):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200)
    length = models.IntegerField(default=0)

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="tracks")

    def __str__(self):
        return self.name


class Car(TimeStampedModel):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200)

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="cars")
    car_class = models.ForeignKey("CarClass", on_delete=models.CASCADE, related_name="cars", null=True)

    def __str__(self):
        return self.name


class CarClass(TimeStampedModel):
    class Meta:
        ordering = [
            "name",
        ]

    name = models.CharField(max_length=200)

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="car_classes")

    def __str__(self):
        return self.name


class SessionType(TimeStampedModel):
    type = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.type


class Session(ExportModelOperationsMixin("session"), DirtyFieldsMixin, TimeStampedModel):
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


class FastLap(ExportModelOperationsMixin("fastlap"), TimeStampedModel):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="fast_laps")
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="fast_laps", null=True)
    # add binary field to hold arbitrary data
    data = PickledObjectField(null=True)

    class Meta:
        ordering = ["game", "car", "track"]

    def __str__(self):
        return f"{self.game} {self.car} {self.track}"


class Lap(ExportModelOperationsMixin("lap"), DirtyFieldsMixin, TimeStampedModel):
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

    def time_human(self):
        minutes = int(self.time // 60)
        seconds = round(self.time % 60, 2)
        # milliseconds = int((coach_lap_time % 1) * 1000)
        time_string = ""
        if minutes > 1:
            time_string += f"{minutes} minutes "
        elif minutes == 1:
            time_string += f"{minutes} minute "

        time_string += f"{seconds:.2f} seconds "

        return time_string


class FastLapSegment(TimeStampedModel):
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


class Coach(ExportModelOperationsMixin("coach"), TimeStampedModel):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    error = models.TextField(default="")
    status = models.TextField(default="")
    enabled = models.BooleanField(default=False)

    fast_lap = models.ForeignKey(FastLap, on_delete=models.SET_NULL, related_name="coaches", null=True)

    MODE_DEFAULT = "default"
    MODE_TRACK_GUIDE = "track_guide"
    MODE_DEBUG = "debug"
    MODE_ONLY_BRAKE = "only_brake"
    MODE_ONLY_BRAKE_DEBUG = "only_brake_debug"
    MODE_CHOICES = [
        (MODE_DEFAULT, "Default"),
        (MODE_TRACK_GUIDE, "Track Guide"),
        (MODE_DEBUG, "Debug"),
        (MODE_ONLY_BRAKE, "Only Brakepoints"),
        (MODE_ONLY_BRAKE_DEBUG, "Only Brakepoints (Debug))"),
    ]
    mode = models.CharField(max_length=64, default=MODE_DEFAULT, choices=MODE_CHOICES)

    def __str__(self):
        return self.driver.name


class Landmark(TimeStampedModel):
    name = models.CharField(max_length=200)
    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    is_overtaking_spot = models.BooleanField(null=True)
    from_cc = models.BooleanField(default=False)

    KIND_MISC = "misc"
    KIND_SEGMENT = "segment"
    KIND_TURN = "turn"
    KIND_CHOICES = [
        (KIND_MISC, "Misc"),
        (KIND_SEGMENT, "Segment"),
        (KIND_TURN, "Turn"),
    ]

    kind = models.CharField(max_length=64, default=KIND_MISC, choices=KIND_CHOICES)

    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="landmarks")

    def __str__(self):
        return self.name


class TrackGuide(TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(default="")
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    def car_game(self):
        return self.car.game

    def __str__(self):
        return f"{self.name}"


class TrackGuideNote(TimeStampedModel):
    track_guide = models.ForeignKey(TrackGuide, on_delete=models.CASCADE, related_name="notes")

    landmark = models.ForeignKey(Landmark, on_delete=models.CASCADE, related_name="notes", null=True)
    segment = models.IntegerField(default=0)

    priority = models.IntegerField(default=0)
    ref_id = models.CharField(max_length=64, default="")
    ref_eval = models.CharField(max_length=64, default="")

    message = models.TextField(default="")
    eval = models.TextField(default="")
    notes = models.TextField(default="")

    def __str__(self):
        where = self.landmark or self.segment
        repr = f"{where}: {self.message}"
        return repr
