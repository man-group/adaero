from __future__ import unicode_literals

import pytest
import transaction

from adaero.models import Period, Enrollee, FeedbackRequest
from adaero.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
)
from adaero.views.enrol import (
    ENROLMENT_EXISTS_TEMPLATE,
    ENROLMENT_ACTIVE_TEMPLATE,
    ENROLMENT_INACTIVE_TEMPLATE,
    ENROLMENT_SUCCESS_TEMPLATE,
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


def test_employee_can_get_correct_enrolment_status_when_in_enrolment_period(
    app_in_enrolment_phase,
):  # noqa: E501
    app = successfully_login(app_in_enrolment_phase, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/enrol", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == "Request feedback"
    assert (
        response.json_body["body"] == "Request feedback from your "
        "colleagues by hitting the "
        "big button below."
    )
    assert response.json_body["buttonText"] == "Request feedback"
    assert response.json_body["buttonLink"] is None
    assert response.json_body["canEnrol"]
    assert response.json_body["heading"] == ENROLMENT_ACTIVE_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLMENT_ACTIVE_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLMENT_ACTIVE_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLMENT_ACTIVE_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canEnrol"] == ENROLMENT_ACTIVE_TEMPLATE["canEnrol"]
    )


@pytest.mark.parametrize(
    "is_enrolled, body", ((True, ENROLLED_BODY), (False, NOT_ENROLLED_BODY))
)
def test_employee_can_get_correct_enrolment_status_when_outside_enrolment_period(
    ldap_mocked_app_with_users, is_enrolled, body
):  # noqa: E501
    dbsession = get_dbsession(ldap_mocked_app_with_users)

    with transaction.manager:
        period = Period(
            name=TEST_PERIOD_NAME,
            enrolment_start_utc=days_from_utcnow(-2),
            entry_start_utc=days_from_utcnow(-1),
            approval_start_utc=days_from_utcnow(2),
            approval_end_utc=days_from_utcnow(3),
        )
        dbsession.add(period)
        if is_enrolled:
            enrollee = Enrollee(username=TEST_EMPLOYEE_USERNAME, period=period)
            dbsession.add(enrollee)

    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/enrol", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLMENT_INACTIVE_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == body
    assert (
        response.json_body["buttonText"] == ENROLMENT_INACTIVE_TEMPLATE["buttonText"]
    )
    assert (
        response.json_body["buttonLink"] == ENROLMENT_INACTIVE_TEMPLATE["buttonLink"]
    )
    assert (
        response.json_body["canEnrol"] == ENROLMENT_INACTIVE_TEMPLATE["canEnrol"]
    )


def test_employee_can_get_correct_enrolment_status_when_already_enrolled(
    app_in_enrolment_phase,
):  # noqa: E501
    dbsession = get_dbsession(app_in_enrolment_phase)

    with transaction.manager:
        period = dbsession.query(Period).first()
        enrollee = Enrollee(period=period, username=TEST_EMPLOYEE_USERNAME)
        dbsession.add(enrollee)

    app = successfully_login(app_in_enrolment_phase, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.get(
        "/api/v1/enrol", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLMENT_EXISTS_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLMENT_EXISTS_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLMENT_EXISTS_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLMENT_EXISTS_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canEnrol"] == ENROLMENT_EXISTS_TEMPLATE["canEnrol"]
    )


def test_employee_can_self_enrol_under_valid_conditions(
    app_in_enrolment_phase,
):  # noqa: E501
    app = successfully_login(app_in_enrolment_phase, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/enrol", headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token}
    )
    assert response.json_body["heading"] == ENROLMENT_SUCCESS_TEMPLATE[
        "heading"
    ].format(period_name=TEST_PERIOD_NAME)
    assert response.json_body["body"] == ENROLMENT_SUCCESS_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert response.json_body["buttonText"] == ENROLMENT_SUCCESS_TEMPLATE["buttonText"]
    assert response.json_body["buttonLink"] == ENROLMENT_SUCCESS_TEMPLATE["buttonLink"]
    assert (
        response.json_body["canEnrol"] == ENROLMENT_SUCCESS_TEMPLATE["canEnrol"]
    )


def test_employee_cannot_self_enrol_if_already_enrolled(
    app_in_enrolment_phase,
):  # noqa: E501
    dbsession = get_dbsession(app_in_enrolment_phase)

    with transaction.manager:
        period = dbsession.query(Period).first()
        enrollee = Enrollee(period=period, username=TEST_EMPLOYEE_USERNAME)
        dbsession.add(enrollee)

    app = successfully_login(app_in_enrolment_phase, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/enrol",
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 400
    assert "You are already enrolled" in response.json_body["message"]


def test_employee_cannot_self_enrol_when_not_in_valid_enrolment_phase(
    ldap_mocked_app_with_users,
):  # noqa: E501
    dbsession = get_dbsession(ldap_mocked_app_with_users)

    with transaction.manager:
        period = Period(
            name=TEST_PERIOD_NAME,
            enrolment_start_utc=days_from_utcnow(-2),
            entry_start_utc=days_from_utcnow(-1),
            approval_start_utc=days_from_utcnow(2),
            approval_end_utc=days_from_utcnow(3),
        )
        dbsession.add(period)

    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    response = app.post(
        "/api/v1/enrol",
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 404


def test_anonymous_cannot_get_enrollees(
    app_with_enrollees_inside_entry_phase,
):  # noqa: E501
    app = app_with_enrollees_inside_entry_phase
    logout(app)

    response = app.get("/api/v1/enrollees", expect_errors=True)
    assert response.status_code == 401


def test_employee_can_list_enrollees_inside_entry_phase(
    app_with_enrollees_and_existing_feedback_form_inside_entry_phase,
):  # noqa: E501
    app = successfully_login(
        app_with_enrollees_and_existing_feedback_form_inside_entry_phase,  # noqa: E501
        TEST_EMPLOYEE_USERNAME,
    )
    response = app.get("/api/v1/enrollees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    # logged in user should not see their own name in enrolment list
    enrollee_usernames = sorted(
        [name for name in TEST_NOMINEES if name != TEST_EMPLOYEE_USERNAME]
    )
    expected = []
    for un in enrollee_usernames:
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
        response.json_body["enrollees"], key=lambda x: x["displayName"]
    )
    assert expected == sorted_response


def test_external_can_list_enrollee_inviters_inside_entry_phase(
    app_with_enrollees_and_existing_feedback_form_inside_entry_phase,
):  # noqa: E501
    app = successfully_login(
        app_with_enrollees_and_existing_feedback_form_inside_entry_phase,  # noqa: E501
        TEST_COMPANY_COLLEAGUE_USERNAME,
    )
    response = app.get("/api/v1/enrollees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    assert response.json_body["enrollees"] == []

    dbsession = get_dbsession(app)
    # add irrevelant external invite for previous period
    add_test_period_with_template(
        dbsession,
        Period.ENTRY_PHASE,
        1,
        period_id=TEST_PREVIOUS_PERIOD_ID,
        period_name=TEST_PREVIOUS_PERIOD_NAME,
        offset_from_utc_now_days=-100,
    )

    with transaction.manager:
        invite = FeedbackRequest(
            to_username=TEST_COMPANY_COLLEAGUE_USERNAME,
            from_username=TEST_EMPLOYEE_USERNAME,
            period_id=TEST_PERIOD_ID,
        )
        dbsession.add(invite)

        prev_invite = FeedbackRequest(
            to_username=TEST_COMPANY_COLLEAGUE_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=TEST_PREVIOUS_PERIOD_ID,
        )
        dbsession.add(prev_invite)

    response = app.get("/api/v1/enrollees")
    assert 200 == response.status_code
    assert TEST_PERIOD_NAME == response.json_body["period"]
    assert 1 == len(response.json_body["requesters"])
    assert TEST_EMPLOYEE_USERNAME == response.json_body["requesters"][0]["username"]
    assert not response.json_body["requesters"][0]["hasExistingFeedback"]
    assert 0 == len(response.json_body["enrollees"])


def test_employee_can_list_enrollees_inside_entry_phase_2(
    ldap_mocked_app_with_users,
):  # noqa: E501
    """A particular DB state that caused failure in the past but
    is not working"""
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, Period.ENTRY_PHASE)

    response = app.get("/api/v1/enrollees")
    assert response.status_code == 200
    assert TEST_PERIOD_NAME == response.json_body["period"]
    # logged in user should not see their own name in enrolment list
    enrollees = [("bboggs", True), ("llovelace", False)]
    expected = []
    for un, has_manager_in_database in enrollees:
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
        response.json_body["enrollees"], key=lambda x: x["displayName"]
    )
    assert len(expected) == len(sorted_response)
    assert expected == sorted_response


def test_employee_cannot_list_enrollees_outside_entry_phase(
    app_with_enrollees_inside_approval_phase,
):  # noqa: E501
    app = successfully_login(
        app_with_enrollees_inside_approval_phase, TEST_EMPLOYEE_USERNAME
    )

    response = app.get("/api/v1/enrollees")
    message = response.json_body["message"]
    assert message["heading"] == ENTRY_ENDED_TEMPLATE["heading"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert message["body"] == ENTRY_ENDED_TEMPLATE["body"].format(
        period_name=TEST_PERIOD_NAME
    )
    assert message["buttonText"] == ENTRY_ENDED_TEMPLATE["buttonText"]
    assert message["buttonLink"] == ENTRY_ENDED_TEMPLATE["buttonLink"]
    assert message["canEnrol"] == ENTRY_ENDED_TEMPLATE["canEnrol"]
