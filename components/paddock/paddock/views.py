from typing import Any, Dict

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic.edit import FormView

import paddock.fastlap_app  # noqa: F401
import paddock.pitcrew_app  # noqa: F401
from telemetry.models import Coach, Driver

# https://gist.github.com/maraujop/1838193
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field
# from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions


class CoachForm(forms.Form):
    driver_name = forms.CharField(
        help_text="The MQTT drivername in CrewChief",
        widget=forms.TextInput(attrs={"placeholder": "-- CrewChief MQTT drivername --"}),
    )
    # PrependedText('field_name', '@', placeholder="username")

    coach_enabled = forms.BooleanField(required=False)
    coach_mode = forms.ChoiceField(
        choices=Coach.MODE_CHOICES,
        label="coaching mode",
    )

    # message = forms.CharField(widget=forms.Textarea)

    # def send_email(self):
    #     # send email using the self.cleaned_data dictionary
    #     pass

    def __init__(self, *args, **kwargs):
        """Grants access to the request object so that only members of the current user
        are given as options"""

        self.request = kwargs.pop("request")
        super(CoachForm, self).__init__(*args, **kwargs)
        # self.fields['members'].queryset = Member.objects.filter(
        #     user=self.request.user)


class CoachView(LoginRequiredMixin, FormView):
    template_name = "coach.html"
    form_class = CoachForm
    success_url = "/coach/"

    # def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
    #     super().setup(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Passes the request object to the form class.
        This is necessary to only display members that belong to a given user"""

        kwargs = super(CoachView, self).get_form_kwargs()
        # https://medium.com/analytics-vidhya/django-how-to-pass-the-user-object-into-form-classes-ee322f02948c
        kwargs["request"] = self.request
        return kwargs

    # def get_messages(self, coach: Coach):
    #     if not coach.fast_lap:
    #         return []

    #     history = History()
    #     pitcrew_coach = PitcrewCoach(history, coach)
    #     pitcrew_coach.track_walk = coach.track_walk
    #     filter = {
    #         "Driver": coach.driver.name,
    #         "GameName": coach.fast_lap.game.name,
    #         "TrackCode": coach.fast_lap.track.name,
    #         "CarModel": coach.fast_lap.car.name,
    #         "SessionId": 666,
    #     }
    #     history.set_filter(filter)
    #     history.init()
    #     pitcrew_coach.init_messages()
    #     messages = []
    #     telemetry = {}
    #     for distance in range(0, history.track_length):
    #         responses = pitcrew_coach.collect_responses(distance, telemetry)
    #         messages.extend(responses)

    #     return messages

    def get_context_data(self, **kwargs):
        """Use this to add extra context."""
        context = super(CoachView, self).get_context_data(**kwargs)
        # context['coach'] = self.request.session['message']
        context["coach"] = "Coach"
        if self.coach:
            context["coach"] = self.coach
            # context["messages"] = self.get_messages(self.coach)
        return context

    def get_initial(self) -> Dict[str, Any]:
        user_name = self.request.user.first_name

        self.coach = None
        coach_enabled = False
        coach_mode = Coach.MODE_DEFAULT
        driver_name = None

        driver = Driver.objects.filter(name=user_name).first()
        if driver:
            driver_name = driver.name
            self.coach = Coach.objects.get_or_create(driver=driver)[0]
            coach_enabled = self.coach.enabled
            coach_mode = self.coach.mode

        data = {
            "driver_name": driver_name,
            "coach_enabled": coach_enabled,
            "coach_mode": coach_mode,
        }
        return data

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        # form.send_email()
        # form.logged_in_user = self.request.user

        # does another user exist with this name?
        driver_name = form.cleaned_data["driver_name"].strip()
        user = User.objects.filter(first_name=driver_name).first()

        if not user or user == self.request.user:
            # driver = Driver.objects.filter(name=form.cleaned_data["driver_name"]).first()
            self.request.user.first_name = form.cleaned_data["driver_name"]
            driver = Driver.objects.filter(name=driver_name).first()
            if driver:
                coach = Coach.objects.get_or_create(driver=driver)[0]
                coach.enabled = form.cleaned_data["coach_enabled"]
                coach.mode = form.cleaned_data["coach_mode"]
                coach.save()

            self.request.user.save()
        return super().form_valid(form)

    # def get(self, request, *args, **kwargs):
    #     # fastlap = get_object_or_404(FastLap, pk=fastlap_id)
    #     # context = {"fastlap": fastlap, "segments": fastlap.fast_lap_segments.all()}  # type: ignore

    #     # get the logged in user
    #     # driver = Driver.objects.get(user=request.user)
    #     context = {
    #         "coach": request.user.first_name,
    #     }  # type: ignore
    #     # return render(request, template_name="coach.html", context=context)
    #     kwargs["context"] = context
    #     return super().get(request, *args, **kwargs)


def index(request):
    return HttpResponse("Paddock is up and running!")


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
    return render(request, template_name=template_name, context={})


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
