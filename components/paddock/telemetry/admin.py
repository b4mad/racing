from django.contrib import admin
from django_admin_relation_links import AdminChangeLinksMixin
from .models import Game, Driver, Car, Track, Session, SessionType, Lap
from .models import FastLap, FastLapSegment
from .models import Coach


class FastLapAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["track"]
    changelist_links = ["fast_lap_segments"]


class FastLapSegmentAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = [
        "fast_lap",
        "turn",
        "start",
        "end",
        "brake",
        "turn_in",
        "force",
        "gear",
        "stop",
        "accelerate",
        "speed",
        "mark",
    ]
    change_links = []


class LapAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "get_driver",
        "valid",
        "number",
        "get_game",
        "track",
        "car",
        "length",
        "time",
        "session",
        "start",
        "end",
    ]

    # https://stackoverflow.com/questions/163823/can-list-display-in-a-django-modeladmin-display-attributes-of-foreignkey-field
    @admin.display(ordering="session__driver", description="Driver")
    def get_driver(self, obj):
        return obj.session.driver

    @admin.display(ordering="session__game", description="Game")
    def get_game(self, obj):
        return obj.session.game


class DriverAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name"]
    changelist_links = ["sessions"]


class SessionAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["session_id", "driver", "game", "session_type", "start", "end"]
    changelist_links = ["laps"]


class TrackAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "game"]
    changelist_links = ["laps"]


class CarAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "game"]
    # changelist_links = ["laps"]


class GameAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name"]
    changelist_links = ["tracks", "cars", "sessions"]


# class CoachInline(admin.TabularInline):
#     model = Coach

# class CoachAdmin(admin.ModelAdmin):
#     model = Coach
#     display = ('name')
# class DriverAdmin(admin.ModelAdmin):
#     model = Driver
#     display = ('name')
#     inlines = [CoachInline, ]


admin.site.register(Car, CarAdmin)
admin.site.register(SessionType)
admin.site.register(Lap, LapAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Driver, DriverAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(FastLap, FastLapAdmin)
admin.site.register(FastLapSegment, FastLapSegmentAdmin)
admin.site.register(Coach)
