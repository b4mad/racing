from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("help/", views.HelpPageView.as_view(), name="help"),
    path("help/install", views.HelpInstallPageView.as_view(), name="help-install"),
    path("copilots/", views.CopilotsOverviewView.as_view(), name="copilots-overview"),
    path("copilot/<pk>", views.CopilotDetailsView.as_view(), name="copilot-details"),
    path("profile/<slug:slug>/", views.ProfileDetailView.as_view(), name="profile"),
    path("profile/<slug:slug>/edit/", views.ProfileUpdateView.as_view(), name="profile-edit"),
    path(
        "profile/<slug:slug>/subscriptions/",
        views.ProfileSubscriptionsUpdateView.as_view(),
        name="profile-subscriptions",
    ),
    path("profile/", views.ProfileRedirectView.as_view(), name="profile-redirector"),
]
