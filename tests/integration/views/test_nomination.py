from __future__ import unicode_literals

import pytest
import transaction

from feedback_tool.models import Period, Nominee, ExternalInvite
from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
)
from feedback_tool.views.nomination import (
    ENROLLMENT_EXISTS_TEMPLATE,
    ENROLLMENT_ACTIVE_TEMPLATE,
    ENROLLMENT_INACTIVE_TEMPLATE,
    ENROLLMENT_SUCCESS_TEMPLATE,
    ENTRY_ENDED_TEMPLATE,
    ENROLLED_BODY,
    NOT_ENROLLED_BODY,
)
from tests.integration.views.conftest import successfully_login, logout

from tests.integration.conftest import get_dbsession, days_from_utcnow
from tests.integration.constants import (
    TEST_EMPLOYEE_USERNAME,
    TEST_PERIOD_NAME,
    TEST_NOMINEES,
    EXISTING_FEEDBACK_FORM_USERNAME,
    TEST_LDAP_FULL_DETAILS,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    TEST_PREVIOUS_PERIOD_ID,
    TEST_PREVIOUS_PERIOD_NAME,
    TEST_PERIOD_ID,
    TEST_MANAGER_USERNAME,
    TEST_USERNAME_KEY,
    MANAGER_KEY,
)
from tests.integration.views.test_manager import (
    add_test_data_for_stats,
    add_test_period_with_template,
)


def test_employee_can_get_correct_nomination_status_when_in_enrollment_period(
    app_in_enrollment_subperiod
):  # noqa: E501
    app = successfully_login(app_in_enrollment_subperiod, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/self-nominate", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == "Request feedback"
    assert (
        response.json_body["body"] == "Request feedback from your "
        "colleagues by hitting the "
        "big button below."
    )
    assert response.json_body["buttonText"] == "Request feedback"
    assert response.json_body["buttonLink"] is None
    assert response.json_body["canNominate"]
    assert response.json_body["heading"] == ENROLLMENT_ACTIVE_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLLMENT_ACTIVE_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLLMENT_ACTIVE_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLLMENT_ACTIVE_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canNominate"] == ENROLLMENT_ACTIVE_TEMPLATE["canNominate"]
    )


@pytest.mark.parametrize(
    "is_enrolled, body", ((True, ENROLLED_BODY), (False, NOT_ENROLLED_BODY))
)
def test_employee_can_get_correct_nomination_status_when_outside_enrollment_period(
    ldap_mocked_app_with_users, is_enrolled, body
):  # noqa: E501
    dbsession = get_dbsession(ldap_mocked_app_with_users)

    with transaction.manager:
        period = Period(
            name=TEST_PERIOD_NAME,
            enrollment_start_utc=days_from_utcnow(-2),
            entry_start_utc=days_from_utcnow(-1),
            approval_start_utc=days_from_utcnow(2),
            approval_end_utc=days_from_utcnow(3),
        )
        dbsession.add(period)
        if is_enrolled:
            nominee = Nominee(username=TEST_EMPLOYEE_USERNAME, period=period)
            dbsession.add(nominee)

    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/self-nominate", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLLMENT_INACTIVE_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == body
    assert (
        response.json_body["buttonText"] == ENROLLMENT_INACTIVE_TEMPLATE["buttonText"]
    )
    assert (
        response.json_body["buttonLink"] == ENROLLMENT_INACTIVE_TEMPLATE["buttonLink"]
    )
    assert (
        response.json_body["canNominate"] == ENROLLMENT_INACTIVE_TEMPLATE["canNominate"]
    )


def test_employee_can_get_correct_nomination_status_when_already_enrolled(
    app_in_enrollment_subperiod
):  # noqa: E501
    dbsession = get_dbsession(app_in_enrollment_subperiod)

    with transaction.manager:
        period = dbsession.query(Period).first()
        nominee = Nominee(period=period, username=TEST_EMPLOYEE_USERNAME)
        dbsession.add(nominee)

    app = successfully_login(app_in_enrollment_subperiod, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/self-nominate", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLLMENT_EXISTS_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLLMENT_EXISTS_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLLMENT_EXISTS_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLLMENT_EXISTS_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canNominate"] == ENROLLMENT_EXISTS_TEMPLATE["canNominate"]
    )


def test_employee_can_self_nominate_under_valid_conditions(
    app_in_enrollment_subperiod
):  # noqa: E501
    app = successfully_login(app_in_enrollment_subperiod, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/self-nominate", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLLMENT_SUCCESS_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLLMENT_SUCCESS_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLLMENT_SUCCESS_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLLMENT_SUCCESS_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canNominate"] == ENROLLMENT_SUCCESS_TEMPLATE["canNominate"]
    )


def test_employee_cannot_self_nominate_if_already_nominated(
    app_in_enrollment_subperiod
):  # noqa: E501
    dbsession = get_dbsession(app_in_enrollment_subperiod)

    with transaction.manager:
        period = dbsession.query(Period).first()
        nominee = Nominee(period=period, username=TEST_EMPLOYEE_USERNAME)
        dbsession.add(nominee)

    app = successfully_login(app_in_enrollment_subperiod, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/self-nominate",
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 400
    assert "You are already enrolled" in response.json_body["message"]


def test_employee_cannot_self_nominate_when_not_in_valid_enrollment_subperiod(
    ldap_mocked_app_with_users
):  # noqa: E501
    dbsession = get_dbsession(ldap_mocked_app_with_users)

    with transaction.manager:
        period = Period(
            name=TEST_PERIOD_NAME,
            enrollment_start_utc=days_from_utcnow(-2),
            entry_start_utc=days_from_utcnow(-1),
            approval_start_utc=days_from_utcnow(2),
            approval_end_utc=days_from_utcnow(3),
        )
        dbsession.add(period)

    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/self-nominate",
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 404


def test_anonymous_cannot_get_nominees(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = app_with_nominees_inside_entry_subperiod
    logout(app)

    response = app.get("/api/v1/nominees", expect_errors=True)
    assert response.status_code == 401


def test_employee_can_list_nominees_inside_entry_subperiod(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_EMPLOYEE_USERNAME,
    )
    response = app.get("/api/v1/nominees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    # logged in user should not see their own name in nomination list
    nominee_usernames = sorted(
        [name for name in TEST_NOMINEES if name != TEST_EMPLOYEE_USERNAME]
    )
    expected = []
    for un in nominee_usernames:
        data = TEST_LDAP_FULL_DETAILS[un]
        un_name = data[TEST_USERNAME_KEY]
        manager = TEST_LDAP_FULL_DETAILS.get(data[MANAGER_KEY])
        if manager:
            manager_display_name = " ".join([manager["givenName"], manager["sn"]])
        else:
            manager_display_name = "-"
        expected.append(
            {
                "username": un_name,
                "displayName": data["givenName"] + " " + data["sn"],
                "position": data["title"],
                "managerDisplayName": manager_display_name,
                "department": data["department"],
                "hasExistingFeedback": True
                if un_name == EXISTING_FEEDBACK_FORM_USERNAME
                else False,
            }
        )

    sorted_response = sorted(
        response.json_body["nominees"], key=lambda x: x["displayName"]
    )
    assert expected == sorted_response


def test_external_can_list_nominee_inviters_inside_entry_subperiod(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_COMPANY_COLLEAGUE_USERNAME,
    )
    response = app.get("/api/v1/nominees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    assert response.json_body["nominees"] == []

    dbsession = get_dbsession(app)
    # add irrevelant external invite for previous period
    add_test_period_with_template(
        dbsession,
        Period.ENTRY_SUBPERIOD,
        1,
        period_id=TEST_PREVIOUS_PERIOD_ID,
        period_name=TEST_PREVIOUS_PERIOD_NAME,
        offset_from_utc_now_days=-100,
    )

    with transaction.manager:
        invite = ExternalInvite(
            to_username=TEST_COMPANY_COLLEAGUE_USERNAME,
            from_username=TEST_EMPLOYEE_USERNAME,
            period_id=TEST_PERIOD_ID,
        )
        dbsession.add(invite)

        prev_invite = ExternalInvite(
            to_username=TEST_COMPANY_COLLEAGUE_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=TEST_PREVIOUS_PERIOD_ID,
        )
        dbsession.add(prev_invite)

    response = app.get("/api/v1/nominees")
    assert 200 == response.status_code
    assert TEST_PERIOD_NAME == response.json_body["period"]
    assert 1 == len(response.json_body["nominees"])
    assert TEST_EMPLOYEE_USERNAME == response.json_body["nominees"][0]["username"]
    assert not response.json_body["nominees"][0]["hasExistingFeedback"]


def test_employee_can_list_nominees_inside_entry_subperiod_2(
    ldap_mocked_app_with_users
):  # noqa: E501
    """A particular DB state that caused failure in the past but
    is not working"""
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, Period.ENTRY_SUBPERIOD)

    response = app.get("/api/v1/nominees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    # logged in user should not see their own name in nomination list
    nominees = [("bboggs", True), ("llovelace", False)]
    expected = []
    for un, has_manager_in_database in nominees:
        data = TEST_LDAP_FULL_DETAILS[un]
        un_name = data[TEST_USERNAME_KEY]
        # if they are not in the User database, then they don't exist so
        # can't put up a display name
        if has_manager_in_database:
            manager = TEST_LDAP_FULL_DETAILS.get(data[MANAGER_KEY])
            manager_display_name = " ".join([manager["givenName"], manager["sn"]])
        else:
            manager_display_name = "-"
        expected.append(
            {
                "username": un_name,
                "displayName": data["givenName"] + " " + data["sn"],
                "position": data["title"],
                "managerDisplayName": manager_display_name,
                "department": data["department"],
                "hasExistingFeedback": True
                if un_name == EXISTING_FEEDBACK_FORM_USERNAME
                else False,
            }
        )

    sorted_response = sorted(
        response.json_body["nominees"], key=lambda x: x["displayName"]
    )
    assert len(expected) == len(sorted_response)
    assert expected == sorted_response


def test_employee_cannot_list_nominees_outside_entry_subperiod(
    app_with_nominees_inside_approval_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_approval_subperiod, TEST_EMPLOYEE_USERNAME
    )

    response = app.get("/api/v1/nominees")
    assert response.json_body["heading"] == ENTRY_ENDED_TEMPLATE["heading"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["body"] == ENTRY_ENDED_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENTRY_ENDED_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENTRY_ENDED_TEMPLATE["buttonLink"]
    assert response.json_body["canNominate"] == ENTRY_ENDED_TEMPLATE["canNominate"]
