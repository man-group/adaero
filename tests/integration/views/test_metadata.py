from __future__ import unicode_literals
import copy
import os

import pytest
import webtest

import feedback_tool.constants

from tests.settings import DEFAULT_TEST_SETTINGS


def test_can_get_correct_metadata_from_config():
    app = webtest.TestApp(feedback_tool.main({}, **DEFAULT_TEST_SETTINGS))
    response = app.get("/api/v1/metadata")
    assert not response.json_body["metadata"]["passwordlessAccess"]
    dev_settings = copy.copy(DEFAULT_TEST_SETTINGS)
    dev_settings[feedback_tool.constants.ALLOW_PASSWORDLESS_ACCESS_KEY] = True
    app = webtest.TestApp(feedback_tool.main({}, **dev_settings))
    response = app.get("/api/v1/metadata")
    assert response.json_body["metadata"]["passwordlessAccess"]


def test_can_get_correct_metadata_from_environment():
    app = webtest.TestApp(feedback_tool.main({}, **DEFAULT_TEST_SETTINGS))
    response = app.get("/api/v1/metadata")
    assert not response.json_body["metadata"]["passwordlessAccess"]
    os.environ["ALLOW_PASSWORDLESS_ACCESS"] = "true"
    response = app.get("/api/v1/metadata")
    assert response.json_body["metadata"]["passwordlessAccess"]


def test_can_get_correct_logo():  # noqa: E501
    dev_settings = copy.copy(DEFAULT_TEST_SETTINGS)
    dev_settings[feedback_tool.constants.LOGO_FILENAME_KEY] = "test.png"
    app = webtest.TestApp(feedback_tool.main({}, **dev_settings))
    resp = app.get('/api/v1/logo.png')
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://localhost/assets/%s' \
        % dev_settings[feedback_tool.constants.LOGO_FILENAME_KEY]
