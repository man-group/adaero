import getpass
import os
import socket

from logging import getLogger as get_logger
from feedback_tool import constants

log = get_logger(__name__)


def get_envvar_name(key):
    return key.split(".")[-1].upper()


def get_config_value(settings, key, default=None, raise_if_not_set=False):
    """
    For a given `key`, provide a value to resolves first to an environment
    variable, else the Pyramid config, else lastly, a default if provided.

    Parameters
    ----------
    settings
    key
    default:
    raise_if_not_set:
        If `True`, then default is ignored if unset and throw an exception.

    Returns
    -------
    Configuration value to use
    """
    envvar_key = get_envvar_name(key)
    val = os.getenv(envvar_key, settings.get(key))
    if isinstance(val, str):
        if val.lower() == "false":
            val = False
        elif val.lower() == "true":
            val = True
    if val is not None:
        return val
    else:
        if raise_if_not_set:
            raise ValueError(
                "`{}` is not set! Please set and try " "again.".format(key)
            )
        return default


def check_if_production(settings):
    hostname = socket.gethostname()
    unix_user = getpass.getuser()
    configured_hostname = get_config_value(settings, constants.PRODUCTION_HOSTNAME_KEY)
    configured_user = get_config_value(settings, constants.PRODUCTION_USER_KEY)
    is_production = hostname == configured_hostname and unix_user == configured_user
    if is_production:
        log.warning(
            "Configured production hostname and user match current "
            "environment so running in production mode."
        )
    else:
        log.warning(
            "Configured production hostname and user (%s, %s) don't "
            "match the current environment (%s, %s) so not running in "
            "production mode."
            % (configured_hostname, configured_user, hostname, unix_user)
        )
    return is_production
