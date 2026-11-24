import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response
    set_rollback()
    logger.exception("Unhandled API error in %s", type(context["view"]).__name__)
    return Response({"detail": "An unexpected server error occurred."}, status=500)
