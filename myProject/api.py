from rest_framework.renderers import JSONRenderer


class ApiJSONRenderer(JSONRenderer):
    """Keep HTTP status codes and field errors intact in the JSON wire format."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context["response"]
        if response.status_code == 204:
            return b""
        key = "error" if response.status_code >= 400 else "data"
        return super().render({key: data}, accepted_media_type, renderer_context)
