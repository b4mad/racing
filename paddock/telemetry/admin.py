from django.contrib import admin
from .models import Game, Driver, Car, Track, Session, SessionType, Lap

admin.site.register([Game, Driver, Car, Track, Session, SessionType, Lap])
