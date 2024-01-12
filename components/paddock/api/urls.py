from django.urls import path

from . import views

urlpatterns = [
    path("api/session/<int:session_id>", views.SessionView.as_view(), name="api_session"),
    path("api/lap/<int:lap_id>", views.LapView.as_view(), name="api_lap"),
]
