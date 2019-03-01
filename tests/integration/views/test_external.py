from base64 import b64decode
from email.parser import Parser
from email.header import decode_header

import pytest
from mock import patch
import transaction

from logging import getLogger as get_logger

import tests.integration.constants
from feedback_tool import constants as app_constants
from feedback_tool.models import ExternalInvite, Period, User
from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
)
from feedback_tool.security import ldapauth
from .conftest import successfully_login, get_dbsession
from ..constants import (
    TEST_EMPLOYEE_USERNAME,
    TEST_COMPANY_COLLEAGUE_EMAIL,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    TEST_PASSWORD,
    TEST_LDAP_FULL_DETAILS,
    TEST_PERIOD_ID,
    TEST_PREVIOUS_PERIOD_ID,
    TEST_PREVIOUS_PERIOD_NAME,
    TEST_MANAGER_USERNAME,
    NOMINATED_USERNAME,
    QUESTION_IDS_AND_TEMPLATES,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_PRODUCTION_HOSTNAME,
    TEST_PRODUCTION_USER,
    TEST_TEMPLATE_ID,
)
from tests.integration.views.test_manager import (
    add_test_period_with_template,
    add_test_template,
)


log = get_logger(__name__)


@pytest.mark.parametrize(
    "subperiod",
    (Period.ENROLLMENT_SUBPERIOD, Period.APPROVAL_SUBPERIOD, Period.REVIEW_SUBPERIOD),
)
def test_employee_unable_to_send_feedback_request_outside_entry_subperiod(
    ldap_mocked_app_with_users, subperiod
):  # noqa: E501
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.APPROVAL_SUBPERIOD, template_id)
    successfully_login(app, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    email = TEST_COMPANY_COLLEAGUE_EMAIL
    resp = app.post_json(
        "/api/v1/external-invite",
        {"email": email},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert resp.status_code == 400


def test_employee_unable_to_send_feedback_request_inside_entry_subperiod_if_not_nominated(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.ENTRY_SUBPERIOD, template_id)
    successfully_login(app, TEST_EMPLOYEE_2_USERNAME)
    resp = app.get("/api/v1/external-invite")
    assert resp.json_body["heading"]
    assert not resp.json_body["canInvite"]


@pytest.mark.parametrize(
    "email, expected",
    (
        (
            "foo@bar.com",
            (
                400,
                "foo@bar.com is not a valid Example Org. email. If you "
                "think it is, please contact support@example.org.",
            ),
        ),
        (TEST_COMPANY_COLLEAGUE_EMAIL, (200, "")),
    ),
)
def test_employee_able_to_send_feedback_request_within_entry_subperiod(
    ldap_mocked_app_with_users, email, expected
):  # noqa: E501
    expected_status_code, expected_msg = expected
    app = ldap_mocked_app_with_users
    ldapsource = ldapauth.build_ldapauth_from_settings(app.app.registry.settings)
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.ENTRY_SUBPERIOD, template_id)
    successfully_login(app, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]

    app.app.registry.settings[app_constants.ENABLE_SEND_EMAIL_KEY] = True

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        sendmail_mock = smtp_mock().sendmail
        gethostname_mock.return_value = TEST_PRODUCTION_HOSTNAME
        getuser_mock.return_value = TEST_PRODUCTION_USER
        resp = app.post_json(
            "/api/v1/external-invite",
            {"email": email},
            headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
            expect_errors=expected_status_code != 200,
        )

    if resp.status_code != 200:
        assert expected_msg == resp.json_body["message"]
        return

    # check invite email that is sent
    parser = Parser()
    assert len(sendmail_mock.call_args_list) == 1
    raw_message = sendmail_mock.call_args_list[0][0][2]
    message_root = parser.parsestr(raw_message)
    inviter = User.create_from_ldap_details(
        ldapsource, TEST_LDAP_FULL_DETAILS[TEST_EMPLOYEE_USERNAME]
    )

    subject_str, encoding = decode_header(message_root["Subject"])[0]
    subject_unicode = subject_str.decode(encoding)
    assert subject_unicode.count(inviter.display_name) == 1

    invite_messages = message_root.get_payload()
    assert invite_messages[0]["Reply-To"] == inviter.email

    invite_plain = b64decode(invite_messages[0].get_payload()).decode("utf-8")
    invite_html = b64decode(invite_messages[1].get_payload()).decode("utf-8")

    app_url = "https://%s/feedback/%s" % (
        TEST_PRODUCTION_HOSTNAME,
        TEST_LDAP_FULL_DETAILS[inviter.username][
            tests.integration.constants.TEST_USERNAME_KEY
        ],
    )

    assert invite_plain.count(app_url) > 0
    assert invite_plain.count(inviter.first_name) > 0
    assert invite_html.count(app_url) > 1
    assert invite_html.count(app_url) % 2 == 0

    after_invite_resp = app.post_json(
        "/api/v1/login",
        {"username": TEST_COMPANY_COLLEAGUE_USERNAME, "password": TEST_PASSWORD},
    )

    assert after_invite_resp.status_code == 200


def test_employee_able_to_invite_twice(ldap_mocked_app_with_users):  # noqa: E501
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.ENTRY_SUBPERIOD, template_id)
    successfully_login(app, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    with patch("smtplib.SMTP") as _:
        success = app.post_json(
            "/api/v1/external-invite",
            {"email": TEST_COMPANY_COLLEAGUE_EMAIL},
            headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        )
        assert success.status_code == 200
        failed = app.post_json(
            "/api/v1/external-invite",
            {"email": TEST_COMPANY_COLLEAGUE_EMAIL},
            headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
            expect_errors=True,
        )
        assert failed.status_code == 200
        invites = (
            dbsession.query(ExternalInvite)
            .filter(
                ExternalInvite.to_username == TEST_COMPANY_COLLEAGUE_USERNAME,
                ExternalInvite.from_username == TEST_EMPLOYEE_USERNAME,
                ExternalInvite.period_id == TEST_PERIOD_ID,
            )
            .all()
        )
        assert len(invites) == 1
        get_resp = app.get("/api/v1/external-invite")
        assert get_resp.json_body["canInvite"]
        assert len(get_resp.json_body["invitees"]) == 1
        invitee = get_resp.json_body["invitees"][0]
        assert invitee["displayName"] == "Alice Alison"
        assert invitee["businessUnit"] == "Bravo"
        assert invitee["department"] == "App Development"
        assert invitee["email"] == TEST_COMPANY_COLLEAGUE_EMAIL


def test_external_user_able_to_give_and_amend_feedback_that_sent_them_invites(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_COMPANY_COLLEAGUE_USERNAME,
    )
    dbsession = get_dbsession(app)

    # add previous period using existing template
    add_test_period_with_template(
        dbsession,
        Period.ENTRY_SUBPERIOD,
        TEST_TEMPLATE_ID,
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

        # add irrevelant external invite for previous period
        prev_invite = ExternalInvite(
            to_username=TEST_COMPANY_COLLEAGUE_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=TEST_PREVIOUS_PERIOD_ID,
        )
        dbsession.add(prev_invite)

    # refer to tests/integration/constants.py for full list of nominated users
    endpoint = "/api/v1/feedback/%s/"
    not_invited_by_resp = app.get(endpoint % NOMINATED_USERNAME, expect_errors=True)
    assert not_invited_by_resp.status_code == 404

    invited_by_resp = app.get(endpoint % TEST_EMPLOYEE_USERNAME)
    assert invited_by_resp.status_code == 200
    assert invited_by_resp.json_body.get("form")

    expected_answers = [
        {"questionId": QUESTION_IDS_AND_TEMPLATES[0][0], "answer": "First answer 1"},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[1][0], "answer": "First answer 2"},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[2][0], "answer": "First answer 3"},
    ]

    log.info("should be creating new form")

    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    put_resp = app.put_json(
        endpoint % TEST_EMPLOYEE_USERNAME,
        {"form": expected_answers},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
    )
    assert put_resp.status_code == 200
