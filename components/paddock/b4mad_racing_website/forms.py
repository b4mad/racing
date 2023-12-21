from django import forms

from telemetry.models import Driver

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
