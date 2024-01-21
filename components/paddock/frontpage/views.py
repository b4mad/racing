from django.views.generic.base import TemplateView

from telemetry.racing_stats import RacingStats


class HomePageView(TemplateView):
    template_name = "site/home.html"

    # add the 15 most current sessions to the context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        stats = RacingStats()
        combos = stats.combos(range=0.25)
        context["combos"] = combos

        return context
