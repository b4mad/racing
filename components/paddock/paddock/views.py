from typing import Any, Dict
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from telemetry.models import Driver, Coach, FastLap
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

from django.views.generic.edit import FormView

from django import forms

# https://gist.github.com/maraujop/1838193
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field
# from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions


class CoachForm(forms.Form):
    driver_name = forms.CharField()
    coach_enabled = forms.BooleanField(required=False)

    # message = forms.CharField(widget=forms.Textarea)

    # def send_email(self):
    #     # send email using the self.cleaned_data dictionary
    #     pass


class CoachView(LoginRequiredMixin, FormView):
    template_name = "coach.html"
    form_class = CoachForm
    success_url = "/coach/"

    # def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
    #     super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Use this to add extra context."""
        context = super(CoachView, self).get_context_data(**kwargs)
        # context['coach'] = self.request.session['message']
        context["coach"] = "Coach"
        if self.coach:
            context["coach_status"] = self.coach.status
            context["coach_error"] = self.coach.error
        return context

    def get_initial(self) -> Dict[str, Any]:
        user_name = self.request.user.first_name

        self.coach = None
        coach_enabled = False
        driver_name = "-- CrewChief MQTT drivername --"

        driver = Driver.objects.filter(name=user_name).first()
        if driver:
            driver_name = driver.name
            self.coach = Coach.objects.get_or_create(driver=driver)[0]
            coach_enabled = self.coach.enabled

        data = {
            "driver_name": driver_name,
            "coach_enabled": coach_enabled,
        }
        return data

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        # form.send_email()

        # does another user exist with this name?
        driver_name = form.cleaned_data["driver_name"]
        user = User.objects.filter(first_name=driver_name).first()
        if not user or user == self.request.user:
            # driver = Driver.objects.filter(name=form.cleaned_data["driver_name"]).first()
            self.request.user.first_name = form.cleaned_data["driver_name"]
            driver = Driver.objects.filter(name=driver_name).first()
            if driver:
                coach = Coach.objects.get_or_create(driver=driver)[0]
                coach.enabled = form.cleaned_data["coach_enabled"]
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


def fastlap_view(request, template_name="fastlap.html", fastlap_id="", **kwargs):
    fastlap = get_object_or_404(FastLap, pk=fastlap_id)
    context = {"fastlap": fastlap, "segments": fastlap.fast_lap_segments.all()}  # type: ignore
    return render(request, template_name=template_name, context=context)


def fastlap_index(request, template_name="fastlap_index.html"):
    # fast_laps = FastLap.objects.filter(driver=None).all()
    fast_laps = FastLap.objects.select_related("game", "car", "track").filter(driver=None).all()
    # sort by str representation of fastlap
    fast_laps = sorted(fast_laps, key=lambda x: str(x))
    context = {
        "fast_laps": fast_laps,
    }

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
