"""paddock URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from . import views
from .views import CoachView

urlpatterns = [
    # path("", views.index, name="home"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("", include("django_prometheus.urls")),
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
    path("coach/", CoachView.as_view(), name="coach"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("explorer/", include("explorer.urls")),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
]
