from logging import getLogger as get_logger
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.events import NewRequest
from pyramid.security import Authenticated, Everyone

from feedback_tool import constants
from feedback_tool.config import get_config_value, get_envvar_name, check_if_production
from feedback_tool.models.user import request_user_callback
from feedback_tool.security.ldapauth import request_ldapauth_callback

log = get_logger(__name__)

USER_SESSION_KEY = "user"
# cookie named aligned with frontend
# https://angular.io/api/common/http/HttpClientXsrfModule
ANGULAR_2_XSRF_TOKEN_COOKIE_NAME = "XSRF-TOKEN"
ANGULAR_2_XSRF_TOKEN_HEADER_NAME = "X-XSRF-TOKEN"
PYRAMID_XSRF_TOKEN_COOKIE_NAME = "X-CSRF-Token"

EXTERNAL_BUSINESS_UNIT_ROLE = "role:external_business_unit"
EMPLOYEE_ROLE = "role:employee"
MANAGER_ROLE = "role:manager"
TALENT_MANAGER_ROLE = "role:talent_manager"
DIRECT_REPORT_PREFIX = "direct_report:"
TRADING_DEPARTMENT_TEMPLATE = "Trading - {}"


def add_cors_callback_builder(allow_origin_domain):
    def add_cors(event):

        headers = "Origin, Content-Type, Accept, Authorization"

        def cors_headers(request, response):
            origin = allow_origin_domain
            response.headers.update(
                {
                    # In production you would be careful with this
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Headers": headers,
                    "Access-Control-Allow-Credentials": "true",
                }
            )

        event.request.add_response_callback(cors_headers)

    return add_cors


class SimpleAuthenticationPolicy(SessionAuthenticationPolicy):
    def authenticated_userid(self, request):
        user = request.user
        if user is not None:
            return user.username
        return None

    def effective_principals(self, request):
        principals = [Everyone]
        user = request.user
        if not user:
            return principals

        principals.append(Authenticated)
        principals.append(user.username)

        if user.is_staff:
            principals.append(EMPLOYEE_ROLE)
        else:
            principals.append(EXTERNAL_BUSINESS_UNIT_ROLE)

        if user.has_direct_reports:
            principals.append(MANAGER_ROLE)
            for direct_report_user in user.direct_reports:
                principal_string = DIRECT_REPORT_PREFIX + direct_report_user.username
                principals.append(principal_string)

        if (
            user.username
            in request.registry.settings[constants.TALENT_MANAGER_USERNAMES_KEY]
        ):
            principals.append(TALENT_MANAGER_ROLE)

        return principals


def setup_cors(config):
    settings = config.get_settings()
    allow_origin_string = get_config_value(settings, constants.CORS_ALLOW_ORIGIN_KEY)
    if allow_origin_string:
        log.warning(
            "CORS enabled. Access-Control-Allow-Origin will be "
            "restricted to %s" % allow_origin_string
        )
        config.add_subscriber(
            add_cors_callback_builder(allow_origin_string), NewRequest
        )


def includeme(config):

    settings = config.get_settings()

    if get_config_value(settings, constants.ALLOW_PASSWORDLESS_ACCESS_KEY):
        log.warning(
            "PASSWORDLESS ACCESS IS ENABLED (has been set in "
            "config %s or envvar %s)"
            % (
                constants.ALLOW_PASSWORDLESS_ACCESS_KEY,
                get_envvar_name(constants.ALLOW_PASSWORDLESS_ACCESS_KEY),
            )
        )

    authn_policy = SimpleAuthenticationPolicy(callback=None)
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.set_default_csrf_options(
        require_csrf=True, header=ANGULAR_2_XSRF_TOKEN_HEADER_NAME
    )
    config.add_request_method(request_user_callback, "user", reify=True)
    config.add_request_method(request_ldapauth_callback, "ldapsource", reify=True)

    config.add_request_method(
        lambda: check_if_production(settings), "is_production", reify=True
    )
    setup_cors(config)
