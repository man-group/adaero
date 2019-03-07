from base64 import b64decode
from datetime import datetime, time
from email.parser import Parser
import os

from freezegun import freeze_time
import pytest
import transaction
from mock import patch

from feedback_tool import mail
from feedback_tool.constants import (
    EMAIL_CODES,
    ENROL_START,
    ENROL_REMINDER,
    ENTRY_START,
    ENTRY_REMINDER,
    APPROVE_START,
    REVIEW_START,
    EMAIL_TEMPLATE_MAP,
    DISPLAYED_HOSTNAME_KEY,
)
from feedback_tool.date import LONDON, HONG_KONG, BOSTON
from feedback_tool.models import Period, User
from feedback_tool.security import ldapauth
from tests.settings import DEFAULT_TEST_SETTINGS
from tests.integration.views.conftest import get_dbsession
from tests.integration.views.test_manager import (
    add_test_data_for_stats,
    TEST_STATS_NON_NOMINATED_USERS,
)
from tests.integration.constants import (
    TEST_LDAP_FULL_DETAILS,
    TEST_MANAGER_USERS,
    SUMMARISED_USERNAMES,
    TEST_UTCNOW,
    TEST_NON_NOMINATED_USERS,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_EMPLOYEES,
    TEST_PRODUCTION_HOSTNAME,
    TEST_PRODUCTION_USER,
    TEST_OTHER_MANAGER_USERNAME,
    TEST_NON_STAFF_USER
)


def test_get_employee_users(app_with_nominees_inside_entry_subperiod):
    app = app_with_nominees_inside_entry_subperiod
    dbsession = get_dbsession(app)
    users = mail.get_employee_users(dbsession)
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    assert {u.username for u in users} == {k for k in TEST_EMPLOYEES}


def test_get_non_nominated_users(app_with_nominees_inside_entry_subperiod):
    app = app_with_nominees_inside_entry_subperiod
    dbsession = get_dbsession(app)
    users = mail.get_non_nominated_users(dbsession)
    assert {u.username for u in users} == {k for k in TEST_NON_NOMINATED_USERS}


def test_get_manager_users(app_with_nominees_inside_entry_subperiod):
    app = app_with_nominees_inside_entry_subperiod
    dbsession = get_dbsession(app)
    users = mail.get_manager_users(dbsession)
    assert {u.username for u in users} == {k for k in TEST_MANAGER_USERS}


def test_get_summarised_users(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    users = mail.get_summarised_users(dbsession)
    assert {u.username for u in users} == {k for k in SUMMARISED_USERNAMES}


@pytest.fixture(scope="module")
def ldapsource():
    return ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)


# US-T-04
@pytest.mark.parametrize(
    "subperiod, num_times, last_sent_email_code, last_sent_template_key, force, last_users",
    (  # noqa: E501
        (
            Period.ENROLLMENT_SUBPERIOD,
            1,
            "ust01",
            ENROL_START,
            False,
            [TEST_LDAP_FULL_DETAILS[k] for k in TEST_EMPLOYEES],
        ),
        (
            Period.ENROLLMENT_SUBPERIOD,
            4,
            "ust01",
            ENROL_REMINDER,
            False,
            [],
        ),  # don't send reminders unlessed forced
        (
            Period.ENROLLMENT_SUBPERIOD,
            6,
            "ust02",
            ENROL_REMINDER,
            True,
            [TEST_LDAP_FULL_DETAILS[k] for k in TEST_STATS_NON_NOMINATED_USERS],
        ),
        (
            Period.ENTRY_SUBPERIOD,
            1,
            "ust03",
            ENTRY_START,
            False,
            [TEST_LDAP_FULL_DETAILS[k] for k in TEST_EMPLOYEES],
        ),
        (
            Period.ENTRY_SUBPERIOD,
            3,
            "ust04",
            ENTRY_REMINDER,
            True,
            [TEST_LDAP_FULL_DETAILS[k] for k in TEST_EMPLOYEES],
        ),
        (
            Period.APPROVAL_SUBPERIOD,
            6,
            "ust05",
            APPROVE_START,
            True,
            [TEST_LDAP_FULL_DETAILS[k] for k in TEST_MANAGER_USERS],
        ),
        (
            Period.REVIEW_SUBPERIOD,
            2,
            "ust06",
            REVIEW_START,
            True,
            [TEST_LDAP_FULL_DETAILS[k] for k in SUMMARISED_USERNAMES],
        ),
    ),
)
def test_send_correct_emails_are_sent_during_subperiods(
    ldap_mocked_app_with_users,  # noqa: E501
    ldapsource,
    subperiod,
    num_times,
    last_sent_email_code,
    last_sent_template_key,
    force,
    last_users,
):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=subperiod)
    settings = {
        "feedback_tool.load_talent_managers_on_app_start": False,
        "feedback_tool.talent_manager_usernames": [TEST_TALENT_MANAGER_USERNAME],
        "feedback_tool.served_on_https": True,
        "feedback_tool.homebase_location": "London",
        "feedback_tool.production_hostname": TEST_PRODUCTION_HOSTNAME,
        "feedback_tool.production_user": TEST_PRODUCTION_USER,
        "feedback_tool.enable_send_email": True,
    }

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        sendmail_mock = smtp_mock().sendmail
        gethostname_mock.return_value = TEST_PRODUCTION_HOSTNAME
        getuser_mock.return_value = TEST_PRODUCTION_USER
        for i in range(num_times):
            kwargs = {"force": force, "delay_s": 0, "delay_between_s": 0}
            if force:
                kwargs["template_key"] = last_sent_template_key

            mail.check_and_send_email(dbsession, ldapsource, settings, **kwargs)

            if i < num_times - 1:
                sendmail_mock.reset_mock()
        with transaction.manager:
            period = Period.get_current_period(dbsession)

            assert period.get_email_flag_by_code(last_sent_email_code) == TEST_UTCNOW
            for code in EMAIL_CODES.difference({last_sent_email_code}):
                assert period.get_email_flag_by_code(code) != TEST_UTCNOW

        if not len(last_users):
            assert 0 == len(sendmail_mock.call_args_list)
            return

        # TODO: why is email a list now?
        confirm_email_call = sendmail_mock.call_args_list.pop(-1)
        normal_emails_calls = sorted(
            sendmail_mock.call_args_list, key=lambda c: c[0][1][0]
        )
        sorted_by_email_users = sorted(last_users, key=lambda v: v["mail"])
        app_link = "https://%s" % TEST_PRODUCTION_HOSTNAME

        assert len(normal_emails_calls) == len(
            normal_emails_calls
        ), "Incorrect number of normal emails sent"

        parser = Parser()

        # normal_emails_calls = sorted_by_email_calls[:-1]
        # confirm_email_call = sorted_by_email_calls[-1]
        for u, c in zip(sorted_by_email_users, normal_emails_calls):
            args = c[0]
            assert u["mail"] == args[1][0]
            generated_raw_message = args[2]
            message_root = parser.parsestr(generated_raw_message)
            messages = message_root.get_payload()
            assert len(messages) == 2
            plain = b64decode(messages[0].get_payload()).decode("utf-8")
            html = b64decode(messages[1].get_payload()).decode("utf-8")
            # assert no non interpolated variables
            assert plain.count("{") == 0
            assert plain.count(u["givenName"]) > 0
            assert plain.count(app_link) > 0

            assert html.count("{") == 0
            assert html.count(u["givenName"]) > 0
            assert html.count(app_link) > 1
            assert html.count(app_link) % 2 == 0
            assert html.count("</html>") == 1

        num_normal_emails = len(normal_emails_calls)
        tm_details = TEST_LDAP_FULL_DETAILS[TEST_TALENT_MANAGER_USERNAME]
        assert tm_details["mail"] == confirm_email_call[0][1][0]

        # Deal with confirm email sent to talent managers
        confirm_raw_message = confirm_email_call[0][2]
        confirm_root = parser.parsestr(confirm_raw_message)
        confirm_messages = confirm_root.get_payload()
        assert len(confirm_messages) == 2

        confirm_plain = b64decode(confirm_messages[0].get_payload()).decode("utf-8")
        confirm_html = b64decode(confirm_messages[1].get_payload()).decode("utf-8")

        for m in [confirm_plain, confirm_html]:
            assert m.count(EMAIL_TEMPLATE_MAP[last_sent_template_key]["summary"]) == 1
            # exclude confirmation email from count
            assert m.count("%s email addresses" % num_normal_emails) == 1
        assert confirm_html.count("</html>") == 1


@pytest.mark.parametrize("with_envvar", (False, True))
def test_hostname_override_works(ldap_mocked_app_with_users, ldapsource, with_envvar):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=Period.ENROLLMENT_SUBPERIOD)
    displayed_hostname = "notfoobar.com"
    assert displayed_hostname != TEST_PRODUCTION_HOSTNAME
    settings = {
        "feedback_tool.talent_manager_usernames": [TEST_OTHER_MANAGER_USERNAME],
        "feedback_tool.served_on_https": True,
        "feedback_tool.homebase_location": "London",
        "feedback_tool.production_hostname": TEST_PRODUCTION_HOSTNAME,
        "feedback_tool.production_user": TEST_PRODUCTION_USER,
        "feedback_tool.enable_send_email": True,
    }

    if with_envvar:
        os.environ["DISPLAYED_HOSTNAME"] = displayed_hostname
    else:
        settings[DISPLAYED_HOSTNAME_KEY] = displayed_hostname

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        sendmail_mock = smtp_mock().sendmail
        gethostname_mock.return_value = TEST_PRODUCTION_HOSTNAME
        getuser_mock.return_value = TEST_PRODUCTION_USER
        mail.check_and_send_email(
            dbsession, ldapsource, settings, template_key=ENROL_START, force=True
        )

        generated_raw_message = sendmail_mock.call_args_list[0][0][2]
        normal_app_link = "https://%s" % TEST_PRODUCTION_HOSTNAME
        overridden_app_link = "https://%s" % displayed_hostname
        parser = Parser()
        message_root = parser.parsestr(generated_raw_message)
        messages = message_root.get_payload()
        plain = b64decode(messages[0].get_payload()).decode("utf-8")
        assert plain.count(normal_app_link) == 0
        assert plain.count(overridden_app_link) > 0


def test_do_not_send_emails_when_not_in_production(
    ldap_mocked_app_with_users, ldapsource
):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    settings = {
        "feedback_tool.talent_manager_usernames": [TEST_TALENT_MANAGER_USERNAME],
        "feedback_tool.homebase_location": "London",
    }

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        sendmail_mock = smtp_mock().sendmail
        gethostname_mock.return_value = "foo"
        getuser_mock.return_value = "bar"
        mail.check_and_send_email(
            dbsession, ldapsource, settings, delay_s=0, delay_between_s=0
        )
        assert 0 == len(sendmail_mock.call_args_list)


def test_emailing_works_with_different_tm_username_config(
    ldap_mocked_app_with_users, ldapsource
):  # noqa: E501
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    json_str = '["%s"]' % TEST_OTHER_MANAGER_USERNAME
    settings = {
        "feedback_tool.talent_manager_usernames": json_str,
        "feedback_tool.homebase_location": "London",
    }

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        sendmail_mock = smtp_mock().sendmail
        gethostname_mock.return_value = "foo"
        getuser_mock.return_value = "bar"
        mail.check_and_send_email(
            dbsession, ldapsource, settings, delay_s=0, delay_between_s=0
        )
        assert 0 == len(sendmail_mock.call_args_list)


@pytest.mark.parametrize(
    "subperiod, location, utc_offset_tuples",
    (  # noqa: E501
        (
            Period.ENROLLMENT_SUBPERIOD,
            LONDON,
            [
                (time(hour=8, minute=59), 0),
                (time(hour=9, minute=10), 0),
                (time(hour=9, minute=24), 6),
            ],
        ),
        (
            Period.ENROLLMENT_SUBPERIOD,
            HONG_KONG,
            [
                (time(hour=0, minute=59), 0),
                (time(hour=1, minute=24), 6),
                (time(hour=9, minute=24), 6),
            ],
        ),
        (
            Period.ENROLLMENT_SUBPERIOD,
            BOSTON,
            [
                (time(hour=0, minute=59), 0),
                (time(hour=1, minute=00), 0),
                (time(hour=9, minute=10), 0),
                (time(hour=13, minute=59), 0),
                (time(hour=14, minute=55), 6),
            ],
        ),
    ),
)
def test_send_emails_according_to_configured_location(
    ldap_mocked_app_with_users,  # noqa: E501
    ldapsource,
    subperiod,
    location,
    utc_offset_tuples,
):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    # so date saved in database is TEST_UTCNOW
    freezer = freeze_time(TEST_UTCNOW)
    freezer.start()
    add_test_data_for_stats(dbsession, current_subperiod=subperiod, days_in=0)
    freezer.stop()
    # needs to be outside configured employees at a minimum
    settings = {
        "feedback_tool.talent_manager_usernames": [TEST_OTHER_MANAGER_USERNAME],
        "feedback_tool.served_on_https": True,
        "feedback_tool.homebase_location": location,
        "feedback_tool.enable_send_email": True,
    }

    with patch("smtplib.SMTP") as smtp_mock, patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        gethostname_mock.return_value = TEST_PRODUCTION_HOSTNAME
        sendmail_mock = smtp_mock().sendmail
        getuser_mock.return_value = TEST_PRODUCTION_USER
        date_ = TEST_UTCNOW.date()

        def check_sent(num, t):
            assert num == sendmail_mock.call_count, (
                "Incorrect number of emails sent for time %s" % t
            )

        for time_, num_sent in utc_offset_tuples:
            new_dt = datetime.combine(date_, time_)
            freezer = freeze_time(new_dt)

            freezer.start()
            mail.check_and_send_email(
                dbsession,
                ldapsource,
                settings,
                force=False,
                delay_s=0,
                delay_between_s=0,
            )
            check_sent(num_sent, time_)
            # email has already sent, won't send again
            mail.check_and_send_email(
                dbsession,
                ldapsource,
                settings,
                force=False,
                delay_s=0,
                delay_between_s=0,
            )
            check_sent(num_sent, time_)
            freezer.stop()
            sendmail_mock.reset_mock()

            period = Period.get_current_period(dbsession)
            period.enrol_email_last_sent = None
            period.enrol_reminder_email_last_sent = None
            period.entry_email_last_sent = None
            period.entry_reminder_email_last_sent = None
            period.review_email_last_sent = None
            period.feedback_available_mail_last_sent = None
            with transaction.manager:
                dbsession.merge(period)
