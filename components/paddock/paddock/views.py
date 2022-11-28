from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from telemetry.models import Driver, Coach


def index(request):
    return HttpResponse("Paddock is up and running!")


def pitcrew_view(request, template_name="pitcrew.html", **kwargs):
    "Example view that inserts content into the dash context passed to the dash application"

    driver_name = request.GET.get("driver", None)
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
