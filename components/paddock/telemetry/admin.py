from django.contrib import admin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter  # ChoiceDropdownFilter,
from django_admin_relation_links import AdminChangeLinksMixin

from .models import (
    Car,
    Coach,
    Driver,
    FastLap,
    FastLapSegment,
    Game,
    Landmark,
    Lap,
    Session,
    SessionType,
    Track,
    TrackGuide,
    TrackGuideNote,
)


class FastLapAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["track"]
    changelist_links = ["fast_lap_segments", "laps"]
    list_display = ["game", "car", "track", "driver"]


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
    # list_filter = ["car", "track"]
    list_filter = (
        # for ordinary fields
        ("valid", DropdownFilter),
        # for choice fields
        # ('valid', ChoiceDropdownFilter),
        # for related fields
        ("car", RelatedDropdownFilter),
        ("track", RelatedDropdownFilter),
    )
    fields = ["number", "valid", "length", "time", "start", "end"]
    changelist_links = ["session"]
    change_links = ["session", "track", "car"]

    # https://stackoverflow.com/questions/163823/can-list-display-in-a-django-modeladmin-display-attributes-of-foreignkey-field
    @admin.display(ordering="session__driver", description="Driver")
    def get_driver(self, obj):
        return obj.session.driver

    @admin.display(ordering="session__game", description="Game")
    def get_game(self, obj):
        return obj.session.game


class DriverAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "created", "modified"]
    changelist_links = ["sessions"]


class SessionAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["session_id", "driver", "game", "session_type", "start", "end"]
    changelist_links = ["laps"]


class TrackAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "game", "created", "modified"]
    changelist_links = ["laps", "landmarks", "fast_laps"]


class CarAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "game"]
    changelist_links = ["laps", "fast_laps"]


class GameAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name"]
    changelist_links = ["tracks", "cars", "sessions"]


# class CoachInline(admin.TabularInline):
#     model = Coach


class CoachAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["driver", "mode", "created", "modified"]
    fields = ["driver", "error", "status", "mode"]

    # changelist_links = ["se"]


class LandmarkAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["name", "kind", "start", "end", "created", "modified"]


class TrackGuideAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["car_game", "car", "track", "name", "created", "modified"]
    changelist_links = ["notes"]


class TrackGuideNoteAdmin(AdminChangeLinksMixin, admin.ModelAdmin):
    list_display = ["segment", "priority", "ref_id", "ref_eval", "message", "eval", "notes"]


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
admin.site.register(Coach, CoachAdmin)
admin.site.register(Landmark, LandmarkAdmin)
admin.site.register(TrackGuide, TrackGuideAdmin)
admin.site.register(TrackGuideNote, TrackGuideNoteAdmin)
