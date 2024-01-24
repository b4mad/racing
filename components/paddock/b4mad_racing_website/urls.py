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
    # path('pitcrew', TemplateView.as_view(template_name='pitcrew.html'), name="pitcrew"),
    # path("fastlap/<str:game>/<str:track>/<str:car>", views.fastlap_index, name="fastlap_index"),
    # path("fastlap/<str:game>/<str:track>>", views.fastlap_index, name="fastlap_index"),
    # path("fastlap/<str:game>/", views.fastlap_index, name="fastlap_index"),
    # path("fastlap/<int:fastlap_id>", views.fastlap_view, name="fastlap"),
    path("fastlap/", views.fastlap, name="fastlap"),
    # path("fastlap_data/<int:fastlap_id>", views.fastlap_data, name="fastlap_data"),
    # path("fastlap/", views.fastlap_index, name="fastlap_index"),
    # path("pitcrew/<str:driver_name>", views.pitcrew_view, name="pitcrew"),
    # path("pitcrew/", views.pitcrew_index, name="pitcrew_index"),
    # path("coach/", CoachView.as_view(), name="coach"),
    path("session/<int:session_id>", views.session, name="session"),
    path("session/<int:session_id>/<int:lap>", views.session, name="session"),
    path("sessions/<int:game_id>/<int:car_id>/<int:track_id>", views.sessions, name="sessions"),
]
