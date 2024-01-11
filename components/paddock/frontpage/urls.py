from django.urls import path
from frontpage.views import AboutPageView, HelpInstallPageView, HelpPageView, HomePageView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("about/", AboutPageView.as_view(), name="about"),
    path("help/", HelpPageView.as_view(), name="help"),
    path("help/install", HelpInstallPageView.as_view(), name="help-install"),
]
