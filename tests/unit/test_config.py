import pytest
import pyramid.testing
import os

from feedback_tool import config
from feedback_tool import constants

DEFAULT_SETTINGS = {
    constants.CHECK_AND_SEND_EMAIL_INT_KEY: "60",
    constants.LOAD_USER_EMAIL_LIST_KEY: '["bob", "dan"]',
    constants.ALLOW_PASSWORDLESS_ACCESS_KEY: True,
}


@pytest.mark.parametrize(
    "envvar, envvar_val, key, expected",
    (
        (
            "CHECK_AND_SEND_EMAIL_INTERVAL_S",
            "90",
            constants.CHECK_AND_SEND_EMAIL_INT_KEY,
            "90",
        ),
        (None, None, constants.CHECK_AND_SEND_EMAIL_INT_KEY, "60"),
        (
            "ALLOW_PASSWORDLESS_ACCESS",
            "true",
            constants.ALLOW_PASSWORDLESS_ACCESS_KEY,
            True,
        ),
        (
            "ALLOW_PASSWORDLESS_ACCESS",
            "false",
            constants.ALLOW_PASSWORDLESS_ACCESS_KEY,
            False,
        ),
        (None, None, constants.ALLOW_PASSWORDLESS_ACCESS_KEY, True),
        (None, None, constants.LOAD_USER_EMAIL_LIST_KEY, '["bob", "dan"]'),
    ),
)
def test_get_config_value(envvar, envvar_val, key, expected):
    configuration = pyramid.testing.setUp(settings=DEFAULT_SETTINGS)
    settings = configuration.get_settings()
    if envvar:
        os.environ[envvar] = envvar_val
    generated = config.get_config_value(settings, key)
    assert expected == generated
    if envvar:
        os.environ.pop(envvar)
