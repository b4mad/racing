from allauth.account.forms import LoginForm, SignupForm
from django import forms


class AccountSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label="First Name")
    last_name = forms.CharField(max_length=30, label="Last Name")

    template_name = "account/signup.html"

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        return user

    def save(self, request):
        # Ensure you call the parent class's save.
        # .save() returns a User object.
        user = super().save(request)

        # Add your own processing here.

        # You must return the original result.
        return user


class AccountsLoginForm(LoginForm):
    template_name = "account/login.html"

    def login(self, *args, **kwargs):
        return super().login(*args, **kwargs)
