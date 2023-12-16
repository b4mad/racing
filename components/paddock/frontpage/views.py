from django.views.generic.base import TemplateView

from telemetry.models import Session


class HomePageView(TemplateView):
    template_name = "site/home.html"

    # add the 15 most current sessions to the context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = Session.objects.order_by("-modified")[:15]
        return context
