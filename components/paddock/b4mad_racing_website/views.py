import json
import logging
from datetime import datetime, timedelta

import b4mad_racing_website.fastlap_app  # noqa: F401
import b4mad_racing_website.pitcrew_app  # noqa: F401
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import BaseModelForm
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from telemetry.models import Car, Coach, Driver, Game, Lap, Session, Track
from telemetry.racing_stats import RacingStats

from .forms import ProfileForm
from .models import Copilot, Profile

logger = logging.getLogger(__name__)


class HomePageView(TemplateView):
    template_name = "site/home.html"

    # add the 15 most current sessions to the context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        stats = RacingStats()
        combos = stats.combos(range=0.25)
        context["combos"] = combos

        return context


class AboutPageView(TemplateView):
    template_name = "site/about.html"


class HelpPageView(TemplateView):
    template_name = "site/help.html"


class HelpInstallPageView(TemplateView):
    template_name = "site/help-install.html"


class CopilotsOverviewView(ListView):
    model = Copilot
    template_name = "copilots/overview.html"


class CopilotDetailsView(DetailView):
    model = Copilot
    template_name = "copilots/details.html"


class ProfileRedirectView(RedirectView):
    """This view will redirect the user to their own profile page or, if the user is not logged in, to the home page."""

    def get(self, request, *args, **kwargs):
        # lets check if the user is logged in
        if request.user.is_authenticated:
            # if the user is logged in, redirect to their profile page
            return redirect(reverse("profile", kwargs={"slug": request.user.username}))

        # if not, redirect to the home page
        return redirect(reverse("home"))


class ProfileDetailView(DetailView):
    model = Profile
    template_name = "profile/details.html"

    def get(self, request, *args, **kwargs):
        # if the profile cant be found, redirect to the home page
        try:
            # if the user is logged in, create a profile if it doesn't exist
            if request.user.is_authenticated:
                self.object, _created = Profile.objects.get_or_create(user=request.user)
            else:
                raise Http404
        except Http404:
            return redirect(reverse("home"))

        # if the profile is not publicly visible and the user is not the owner of the profile, return 403
        if (not self.object.publicly_visible) and (not request.user == self.object.user):
            return redirect(reverse("home"))

        context = self.get_context_data(object=self.object)
        context["is_myself"] = self.object.user == request.user

        # Let's use the logged in user's profile name to find a Driver
        if self.request.user.is_authenticated:
            try:
                context["driver"] = Driver.objects.get(name=self.request.user.profile.mqtt_drivername)
            except Driver.DoesNotExist:
                context["driver"] = None
                messages.add_message(
                    request, messages.WARNING, "We CANT find you mqtt driver name in the telemetry database."
                )

            # now get the last 5 sessons for this driver
            if context["driver"]:
                context["sessions"] = Session.objects.filter(driver=context["driver"]).order_by("-created")[:5]

                stats = RacingStats()
                circuit_combos = stats.driver_combos(context["driver"])
                context["circuit_combos"] = circuit_combos

                rally_combos = stats.driver_combos(context["driver"], type="rally")
                context["rally_combos"] = rally_combos

        return self.render_to_response(context)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    # fields = ["newsletter_allowed", "publicly_visible", "mqtt_drivername"]
    form_class = ProfileForm

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # This method is called when valid form data has been POSTed.

        # FIXME: this has to be done in the model instead of the view
        # enable the coach and set it to copilots mode
        mqtt_drivername = self.object.mqtt_drivername
        driver = Driver.objects.filter(name=mqtt_drivername).first()
        if driver:
            self.object.driver = driver
            self.object.save()
            coach = Coach.objects.get_or_create(driver=driver)[0]
            coach.enabled = True
            coach.mode = Coach.MODE_COPILOTS
            coach.save()
        return super().form_valid(form)


class ProfileSubscriptionsUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    fields = ["mqtt_drivername"]

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["PUT", "DELETE"])

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["PUT", "DELETE"])

    # pylint: disable=arguments-differ
    def put(self, request, *args, **kwargs):
        # Check if the user is updating their own profile
        if request.user.username != kwargs["slug"]:
            return JsonResponse({"status": "error", "message": "You can't update another user's profile"}, status=403)

        # Check if the content type is application/json
        if request.content_type != "application/json":
            return JsonResponse({"status": "error", "message": "Invalid content type"}, status=415)

        # Get the data from the request
        try:
            data = json.loads(request.body)
            copilot_id = data.get("copilot_id")
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"}, status=400)

        # Check if the copilot exists
        try:
            _ = Copilot.objects.get(pk=copilot_id)
        except Copilot.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Copilot does not exist"}, status=404)

        # Update the user's subscriptions based on the received data
        request.user.profile.subscribe_copilot(copilot_id)
        logger.debug("subscribe copilot %s to user %s, saving...", copilot_id, request.user.username)

        # Return a JSON response with status code 204
        return JsonResponse({}, status=204)

    def delete(self, request, *args, **kwargs):
        """This method will remove the copilot from the user's profile.subscriptions."""

        # Check if the user is updating their own profile
        if request.user.username != kwargs["slug"]:
            return JsonResponse({"status": "error", "message": "You can't update another user's profile"}, status=403)

        # Get the data from the request
        try:
            data = json.loads(request.body)
            copilot_id = data.get("copilot_id")
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"}, status=400)

        # Check if the copilot exists
        try:
            _ = Copilot.objects.get(pk=copilot_id)
        except Copilot.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Copilot does not exist"}, status=404)

        # delete the copilot from the user's subscriptions
        request.user.profile.unsubscribe_copilot(copilot_id)
        logger.debug("subsubscript copilot %s from user %s, saving...", copilot_id, request.user.username)

        # Return a JSON response with status code 204
        return JsonResponse({}, status=204)


def fastlap(request, template_name="fastlap.html", fastlap_id="", **kwargs):
    driver_name = ""
    if request.user.is_authenticated:
        user_name = request.user.first_name
        driver = Driver.objects.filter(name=user_name).first()
        if driver:
            driver_name = driver.name
    context = dict()
    dash_context = request.session.get("django_plotly_dash", dict())
    dash_context["driver_name"] = driver_name
    request.session["django_plotly_dash"] = dash_context
    return render(request, template_name=template_name, context=context)


def session(request, template_name="session.html", **kwargs):
    session_id = kwargs.get("session_id", None)
    lap = kwargs.get("lap", None)
    session = get_object_or_404(Session, session_id=session_id)
    context = {}
    # if the session has any laps
    if session.laps.count() > 0:
        # get all laps with the same game_id / car_id / track_id
        lap = session.laps.first()
        track_id = lap.track_id
        car_id = lap.car_id
        context["track"] = lap.track
        context["car"] = lap.car

        compare_laps = (
            Lap.objects.filter(car_id=car_id, track_id=track_id)
            .filter(valid=True)
            .filter(time__gte=0)
            .filter(fast_lap__isnull=False)
            .order_by("time")[:5]
        )
    else:
        compare_laps = []

    game = session.game
    if game.name in ["Richard Burns Rally"]:
        map_data = True
    else:
        map_data = False

    context["session"] = session
    context["lap_number"] = lap
    context["compare_laps"] = compare_laps
    context["map_data"] = map_data

    return render(request, template_name=template_name, context=context)


def sessions(request, template_name="sessions.html", **kwargs):
    game_id = kwargs.get("game_id", None)
    car_id = kwargs.get("car_id", None)
    track_id = kwargs.get("track_id", None)

    context = {}

    sessions = []
    filter = {}
    if game_id:
        filter["game_id"] = game_id
        context["game"] = Game.objects.get(pk=game_id)
    if car_id:
        filter["laps__car_id"] = car_id
        context["car"] = Car.objects.get(pk=car_id)
    if track_id:
        filter["laps__track_id"] = track_id
        context["track"] = Track.objects.get(pk=track_id)

    # Calculate the start date based on the range
    start_date = datetime.now() - timedelta(days=14)

    # Filter laps based on the end time within the range
    filter["end__gte"] = start_date

    # get the sessions that are
    # eager load laps and game
    sessions = Session.objects.filter(**filter).order_by("-created")
    sessions = sessions.prefetch_related("game", "laps__car", "laps__track")
    sessions = sessions.distinct()

    context["sessions"] = sessions

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
    context = {
        "drivers": drivers,
        "drivers_total": drivers_total,
    }

    return render(request, template_name=template_name, context=context)
