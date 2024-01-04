import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import BaseModelForm
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from telemetry.models import Coach, Driver, Session

from .forms import ProfileForm
from .models import Copilot, Profile

logger = logging.getLogger(__name__)


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
