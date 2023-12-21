from django.contrib import admin

from .models import Copilot, CopilotInstance, Profile

admin.site.register(Profile, list_display=["user", "mqtt_drivername", "driver"])
admin.site.register(Copilot)
admin.site.register(CopilotInstance, list_display=["driver", "copilot", "enabled"])
