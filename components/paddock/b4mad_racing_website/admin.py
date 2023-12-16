from django.contrib import admin

from .models import Copilot, CopilotInstance, Profile

admin.site.register(Profile)
admin.site.register(Copilot)
admin.site.register(CopilotInstance)
