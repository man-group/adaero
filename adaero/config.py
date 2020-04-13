import os

from logging import getLogger as get_logger

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

