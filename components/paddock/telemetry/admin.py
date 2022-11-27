from django.contrib import admin
from .models import Game, Driver, Car, Track, Session, SessionType, Lap
from .models import FastLap, FastLapSegment

admin.site.register([Game, Driver, Car, Track, Session, SessionType, Lap])
admin.site.register([FastLap, FastLapSegment])
