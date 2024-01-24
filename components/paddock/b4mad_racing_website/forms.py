from typing import Any, Dict

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic.edit import FormView

from telemetry.models import Coach, Driver

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "mqtt_drivername",
            "publicly_visible",
            "newsletter_allowed",
        ]
        help_texts = {
            "mqtt_drivername": "The MQTT drivername in CrewChief",
        }

    def clean(self):
        cleaned_data = super().clean()
        mqtt_drivername = cleaned_data.get("mqtt_drivername").strip()

        driver = Driver.objects.filter(name__iexact=mqtt_drivername).first()
        if not driver:
            self.add_error("mqtt_drivername", "Driver name does not exist. Drive some laps first.")
        else:
            # find a user with this name, case insensitive
            profile = Profile.objects.filter(mqtt_drivername__iexact=mqtt_drivername).first()
            # user = User.objects.filter(first_name=driver_name).first()
            if profile and profile != self.instance:
                self.add_error("mqtt_drivername", "This name is already taken.")
            if mqtt_drivername.lower() == "jim":
                self.add_error("mqtt_drivername", "No Jim allowed.")


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
