from __future__ import unicode_literals

from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.httpexceptions import HTTPFound
from rest_toolkit import resource

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.views import Root


@resource("/api/v1/metadata")
class Metadata(Root):
    def __init__(self, request):  # pylint disable=unused-argument
        pass


@Metadata.GET(permission=NO_PERMISSION_REQUIRED)
def get_metadata(request):
    """
    Return data that can be used to personalize the current user's UI
    """
    is_pwl_access = bool(
        get_config_value(
            request.registry.settings, constants.ALLOW_PASSWORDLESS_ACCESS_KEY
        )
    )
    unit_name = get_config_value(request.registry.settings, constants.BUSINESS_UNIT_KEY)
    login_password_message = get_config_value(
        request.registry.settings, constants.LOGIN_PASSWORD_MSG_KEY
    )
    login_username_message = get_config_value(
        request.registry.settings, constants.LOGIN_USERNAME_MSG_KEY
    )
    support_email = get_config_value(
        request.registry.settings, constants.SUPPORT_EMAIL_KEY
    )
    display_name = get_config_value(
        request.registry.settings, constants.COMPANY_NAME_KEY
    )
    return {
        "metadata": {
            "businessUnit": unit_name,
            "displayName": display_name,
            "loginPasswordMessage": login_password_message,
            "loginUsernameMessage": login_username_message,
            "passwordlessAccess": is_pwl_access,
            "supportEmail": support_email,
        }
    }


@resource("/api/v1/logo.png")
class Logo(Root):
    def __init__(self, request):  # pylint disable=unused-argument
        pass


@Logo.GET(permission=NO_PERMISSION_REQUIRED)
def redirect_logo(request):
    logo_filename = get_config_value(
        request.registry.settings, constants.LOGO_FILENAME_KEY, "logo.png"
    )
    is_https = get_config_value(
        request.registry.settings, constants.SERVED_ON_HTTPS_KEY
    )
    raise HTTPFound(
        request.route_url(
            "catchall_static",
            subpath="assets/%s" % str(logo_filename),
            _scheme="https" if is_https else None,
        )
    )
