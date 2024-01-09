import json

from django.http import JsonResponse
from django.views import View

from .telemetry_loader import TelemetryLoader


class SessionView(View):
    template_name = "session.html"

    def get(self, request, session_id=0, *args, **kwargs):
        telemetry_loader = TelemetryLoader(caching=True)
        df = telemetry_loader.get_session_df(session_id)

        # Compression:
        # Compress the JSON response. Django can be configured to gzip responses, which can significantly reduce the response size.
        # Make sure your frontend can handle the decompression, which is typically handled automatically by modern browsers.

        # render the dataframe as json
        df_json = df.to_json(orient="split", date_format="iso")

        df_dict = json.loads(df_json)

        return JsonResponse(df_dict, safe=False)
