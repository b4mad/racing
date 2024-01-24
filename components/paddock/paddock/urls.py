"""paddock URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("b4mad_racing_website.urls")),
    path("", include("django_prometheus.urls")),
    path("", include("api.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("explorer/", include("explorer.urls")),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
)  # https://stackoverflow.com/questions/39907281/django-uwsgi-static-files-not-being-served-even-after-collectstatic
