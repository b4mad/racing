from allauth.socialaccount.models import SocialAccount
from django.http import HttpResponse

import paddock.metrics as metrics
from telemetry.models import Coach, Driver


def index(request):
    drivers = Driver.objects.count()
    coaches = Coach.objects.count()
    social_accounts = SocialAccount.objects.count()

    metrics.drivers.set(drivers)
    metrics.coaches.set(coaches)
    metrics.social_accounts.set(social_accounts)

    return HttpResponse("recalculated metrics")
