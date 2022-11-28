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


# class CoachInline(admin.TabularInline):
#     model = Coach

# class CoachAdmin(admin.ModelAdmin):
#     model = Coach
#     display = ('name')
# class DriverAdmin(admin.ModelAdmin):
#     model = Driver
#     display = ('name')
#     inlines = [CoachInline, ]


admin.site.register([Game, Car, Track, Session, SessionType, Lap])
admin.site.register(Driver)
admin.site.register(FastLap, FastLapAdmin)
admin.site.register(FastLapSegment, FastLapSegmentAdmin)
admin.site.register(Coach)
