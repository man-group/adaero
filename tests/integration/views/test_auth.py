from __future__ import unicode_literals

from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
)
from ..constants import TEST_MANAGER_USERNAME, TEST_PASSWORD, TEST_LDAP_FULL_DETAILS
from .conftest import successfully_login


def test_login(ldap_mocked_app_with_users):
    """GIVEN I am unauthenticated
    WHEN I login with the correct credentials
    THEN I am returned an XSRF token as a cookie and my user details"""

    app = ldap_mocked_app_with_users

    response = app.post_json(
        "/api/v1/login",
        {"username": "hacker", "password": "ishouldnotwork"},
        expect_errors=True,
    )

    assert ANGULAR_2_XSRF_TOKEN_COOKIE_NAME not in app.cookies
    assert response.status_code == 401, response.json

    response = app.post_json(
        "/api/v1/login", {"username": TEST_MANAGER_USERNAME, "password": TEST_PASSWORD}
    )

    manager_details = TEST_LDAP_FULL_DETAILS[TEST_MANAGER_USERNAME]
    display_name = " ".join([manager_details["givenName"], manager_details["sn"]])
    title = TEST_LDAP_FULL_DETAILS[TEST_MANAGER_USERNAME]["title"]
    generated_principals = [
        "system.Everyone",
        "system.Authenticated",
        "chasmith",
        "role:employee",
        "role:manager",
        "direct_report:ssholes",
        "direct_report:bboggs",
        "direct_report:ddodson",
    ]

    assert True is response.json_body["success"]
    assert display_name == response.json_body["data"]["displayName"]
    assert title == response.json_body["data"]["title"]
    assert "Alpha" == response.json_body["data"]["businessUnit"]
    assert sorted(generated_principals) == sorted(
        response.json_body["data"]["principals"]
    )
    assert ANGULAR_2_XSRF_TOKEN_COOKIE_NAME in app.cookies


def test_logout(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users
    successfully_login(app, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    app.post("/api/v1/logout", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token})


def test_user_data(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users

    failed_resp = app.get("/api/v1/user-data", expect_errors=True)
    assert 401 == failed_resp.status_code

    app.post_json(
        "/api/v1/login", {"username": TEST_MANAGER_USERNAME, "password": TEST_PASSWORD}
    )

    response = app.get("/api/v1/user-data")
    manager_details = TEST_LDAP_FULL_DETAILS[TEST_MANAGER_USERNAME]
    display_name = " ".join([manager_details["givenName"], manager_details["sn"]])
    title = TEST_LDAP_FULL_DETAILS[TEST_MANAGER_USERNAME]["title"]
    generated_principals = [
        "system.Everyone",
        "system.Authenticated",
        "chasmith",
        "role:employee",
        "role:manager",
        "direct_report:ssholes",
        "direct_report:bboggs",
        "direct_report:ddodson",
    ]

    assert True is response.json_body["success"]
    assert display_name == response.json_body["data"]["displayName"]
    assert title == response.json_body["data"]["title"]
    assert "Alpha" == response.json_body["data"]["businessUnit"]
    assert sorted(generated_principals) == sorted(
        response.json_body["data"]["principals"]
    )
    assert ANGULAR_2_XSRF_TOKEN_COOKIE_NAME in app.cookies
