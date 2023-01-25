from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from telemetry.models import Driver, Coach, FastLap


def index(request):
    return HttpResponse("Paddock is up and running!")


def fastlap_view(request, template_name="fastlap.html", fastlap_id="", **kwargs):
    fastlap = get_object_or_404(FastLap, pk=fastlap_id)
    context = {"fastlap": fastlap, "segments": fastlap.fast_lap_segments.all()}  # type: ignore
    return render(request, template_name=template_name, context=context)


def pitcrew_view(request, template_name="pitcrew.html", driver_name="", **kwargs):
    "Example view that inserts content into the dash context passed to the dash application"

    # driver_name = request.GET.get("driver", None)
    if driver_name.lower() == "jim":
        raise Exception("no jim allowed")

    driver = get_object_or_404(Driver, name=driver_name)
    coach = Coach.objects.get_or_create(driver=driver)[0]

    # https://github.com/GibbsConsulting/django-plotly-dash/issues/378
    context = {"init_args": {"power-switch": {"value": coach.enabled}}}

    # create some context to send over to Dash:
    dash_context = request.session.get("django_plotly_dash", dict())
    dash_context["driver_pk"] = driver.pk
    dash_context["enabled"] = coach.enabled
    request.session["django_plotly_dash"] = dash_context

    return render(request, template_name=template_name, context=context)


def pitcrew_index(request, template_name="pitcrew_index.html", **kwargs):

    drivers = Driver.objects.order_by("name")
    drivers_total = drivers.count()
    fast_laps = FastLap.objects.filter(driver=None).all()
    context = {
        "drivers": drivers,
        "drivers_total": drivers_total,
        "fast_laps": fast_laps,
    }

    return render(request, template_name=template_name, context=context)
