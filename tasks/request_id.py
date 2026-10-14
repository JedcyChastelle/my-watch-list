"""Identifiant de requête : relie une ligne de log nginx aux lignes de log Django."""
import contextvars
import logging
import uuid

_request_id = contextvars.ContextVar("request_id", default="-")


class RequestIDMiddleware:
    """Récupère l'en-tête X-Request-ID envoyé par nginx (ou en crée un)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response["X-Request-ID"] = request_id
        return response


class RequestIDFilter(logging.Filter):
    """Ajoute request_id à chaque ligne de log."""

    def filter(self, record):
        record.request_id = _request_id.get()
        return True