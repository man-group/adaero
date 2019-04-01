from datetime import datetime

from pyramid.httpexceptions import HTTPBadRequest, HTTPInternalServerError
from pyramid.view import view_config, notfound_view_config, forbidden_view_config

from logging import getLogger as get_logger

log = get_logger(__name__)


@view_config(context=HTTPBadRequest, renderer="json")
def bad_request(exc, request):
    request.response.status_code = 400
    return {"message": exc.explanation}


@view_config(context=HTTPInternalServerError, renderer="json")
def internal_error(exc, request):
    request.response.status_code = 400
    if getattr(exc, "explanation"):
        message = exc.explanation
    else:
        message = "%s - Internal error on server" % datetime.utcnow()
    return {"message": message}


@notfound_view_config(renderer="json")
def not_found(exc, request):
    log.info("Page Not Found: %s", request.path_url)
    request.response.status_code = 404
    return {"message": exc.explanation}


@forbidden_view_config(renderer="json")
def forbidden(request):
    if request.unauthenticated_userid:
        log.warning("Forbidden: %s for %s", request.path_url, request.user.username)
        request.response.status_int = 403
        payload = {"message": "You are not allowed to perform this action"}
        if request.registry.settings.get("feedback_tool.debug_all"):
            payload["user"] = request.user.to_dict()
        return payload
    else:
        request.response.status_int = 401
        return {"message": "You must login to perform this action"}
