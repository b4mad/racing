from django.urls import path

from . import views

urlpatterns = [
    path("api/session/<int:session_id>", views.SessionView.as_view(), name="session"),
]
