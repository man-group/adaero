from functools import partial

from freezegun import freeze_time
import pytest
import transaction
import webtest
from mock import patch

import feedback_tool
import tests.integration.constants
from feedback_tool.security import ldapauth
from feedback_tool.models import (
    FeedbackQuestion,
    FeedbackTemplateRow,
    FeedbackTemplate,
    Period,
    Nominee,
    FeedbackForm,
    FeedbackAnswer,
    User,
    generate_period_dates,
)

from ..conftest import get_dbsession, days_from_utcnow, drop_everything_but_users
from tests.settings import DEFAULT_TEST_SETTINGS
from ..constants import (
    TEST_UTCNOW,
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_PASSWORD,
    TEST_PERIOD_NAME,
    TEST_PERIOD_ID,
    TEST_FORM_1_ID,
    TEST_FORM_2_ID,
    TEST_FORM_1_ANSWER_1_ID,
    TEST_FORM_1_ANSWER_2_ID,
    TEST_FORM_2_ANSWER_1_ID,
    TEST_LDAP_FULL_DETAILS,
    QUESTION_IDS_AND_TEMPLATES,
    TEST_NOMINEES,
    EXISTING_FEEDBACK_FORM_USERNAME,
    TEST_FORM_2_ANSWER_2_ID,
    TEST_FORM_1_ANSWER_3_ID,
    TEST_FORM_2_ANSWER_3_ID,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    USERNAMES,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_PREVIOUS_PERIOD_ID,
    TEST_SUMMARY_ANSWERS,
    TEST_EMPLOYEES,
    TEST_TEMPLATE_ID,
    TEST_BUSINESS_UNIT_KEY,
    TEST_NON_STAFF_USER,
)


def auth_user_mock_fn(self, username, password):
    return username in USERNAMES and password == TEST_PASSWORD


def get_ldap_user_by_username_mock_fn(self, username):
    if username not in USERNAMES:
        pytest.fail("username %s not in %s" % (username, USERNAMES))
    return TEST_LDAP_FULL_DETAILS[username]


def get_ldap_by_email_mock_fn(self, email):
    ahl_emails = [
        u["mail"]
        for u in TEST_LDAP_FULL_DETAILS.values()
        if u[tests.integration.constants.TEST_USERNAME_KEY] in TEST_EMPLOYEES
    ]
    return (
        TEST_LDAP_FULL_DETAILS[TEST_COMPANY_COLLEAGUE_USERNAME]
        if email not in ahl_emails
        else None
    )


def get_all_ldap_users_mock_fn(self, business_unit):
    return [
        item
        for item in TEST_LDAP_FULL_DETAILS.values()
        if item[TEST_BUSINESS_UNIT_KEY] == business_unit
    ]


@pytest.yield_fixture(scope="session")
def new_ldap_mocked_app_with_users(dbsession, request):
    settings = DEFAULT_TEST_SETTINGS
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    if request.config.getoption("--use-sqlite3"):
        settings["feedback_tool.use_local_sqlite3"] = True

    # need yield_fixture as we need the patch applied over the lifetime of
    # the testapp instance
    with patch(
        "feedback_tool.security.ldapauth.LDAPAuth.auth_user",
        side_effect=auth_user_mock_fn,
        autospec=True,
    ), patch(
        "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_username",
        side_effect=get_ldap_user_by_username_mock_fn,
        autospec=True,
    ), patch(
        "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_email",
        side_effect=get_ldap_by_email_mock_fn,
        autospec=True,
    ):

        app = webtest.TestApp(feedback_tool.main({}, **settings))

        dbsession = get_dbsession(app)

        with transaction.manager:
            for user_details in TEST_LDAP_FULL_DETAILS.values():
                if (
                    user_details[tests.integration.constants.TEST_USERNAME_KEY]
                    not in TEST_EMPLOYEES
                ):
                    continue
                user = User.create_from_ldap_details(ldapsource, user_details)
                set_as_staff(user, user_details)
                dbsession.add(user)

            # Add non-staff member e.g. upper management
            non_staff_user = User.create_from_ldap_details(ldapsource, TEST_NON_STAFF_USER)
            dbsession.add(non_staff_user)

        freezer = freeze_time(TEST_UTCNOW)
        freezer.start()
        yield app
        freezer.stop()


@pytest.yield_fixture
def ldap_mocked_app_with_users(new_ldap_mocked_app_with_users):
    """
    Properly setup, yield and teardown an Oracle backed Pyramid web server
    wrapped with WebTest and LDAP mocked to allow only the TEST credentials
    to authenticate
    """
    app = new_ldap_mocked_app_with_users
    yield app
    dbsession = get_dbsession(app)
    drop_everything_but_users(dbsession)


def successfully_login(app, username):
    app.post_json("/api/v1/login", {"username": username, "password": TEST_PASSWORD})
    return app


def logout(app):
    app.post_json("/api/v1/logout")


@pytest.fixture
def authenticated_app(ldap_mocked_app_with_users, username):
    successfully_login(ldap_mocked_app_with_users, username)
    return ldap_mocked_app_with_users


def add_template(_dbsession, questions, template_id):
    with transaction.manager:
        rows = []
        for row_num, item in enumerate(questions):
            kwargs = {}
            question = FeedbackQuestion(
                id=item[0],
                question_template=item[1],
                caption=item[2],
                answer_type=u"string",
                **kwargs
            )
            row = FeedbackTemplateRow(position=row_num, question=question)
            rows.append(row)
        template = FeedbackTemplate(id=template_id, rows=rows)
        _dbsession.add(template)
    return template.id


def add_test_template(
    _dbsession, questions=QUESTION_IDS_AND_TEMPLATES, template_id=TEST_TEMPLATE_ID
):
    return add_template(_dbsession, questions, template_id)


def add_test_period_with_template(
    dbsession,
    subperiod,
    template_id,
    period_id=TEST_PERIOD_ID,
    period_name=TEST_PERIOD_NAME,
    offset_from_utc_now_days=0,
    add_nominees=True,
    days_in=1,
):

    days_away = partial(days_from_utcnow, offset=offset_from_utc_now_days)
    times = generate_period_dates(subperiod, days_away, days_in)
    with transaction.manager:
        period = Period(
            id=period_id, name=period_name, template_id=template_id, **times
        )
        dbsession.add(period)

    with transaction.manager:
        if add_nominees:
            for nominee_username in TEST_NOMINEES:
                dbsession.add(Nominee(period_id=period_id, username=nominee_username))
    return period_id


@pytest.yield_fixture
def app_with_nominees_inside_entry_subperiod(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.ENTRY_SUBPERIOD, template_id)
    yield app


@pytest.yield_fixture
def app_with_nominees_inside_approval_subperiod(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    template_id = add_test_template(dbsession)
    add_test_period_with_template(dbsession, Period.APPROVAL_SUBPERIOD, template_id)
    yield app


def _add_test_feedback_forms(_dbsession, period_id=TEST_PERIOD_ID):
    with transaction.manager:
        form = FeedbackForm(
            id=TEST_FORM_1_ID,
            to_username=EXISTING_FEEDBACK_FORM_USERNAME,
            from_username=TEST_EMPLOYEE_USERNAME,
            period_id=period_id,
        )
        answers = [
            FeedbackAnswer(
                id=TEST_FORM_1_ANSWER_1_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=u"Foo",
            ),
            FeedbackAnswer(
                id=TEST_FORM_1_ANSWER_2_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=u"Bar",
            ),
            FeedbackAnswer(
                id=TEST_FORM_1_ANSWER_3_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=u"Baz",
            ),
        ]
        form.answers = answers
        _dbsession.add(form)

        form = FeedbackForm(
            id=TEST_FORM_2_ID,
            to_username=EXISTING_FEEDBACK_FORM_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=period_id,
        )
        # because of test_employee_cannot_give_feedback_form_with_missing
        # _answers_to_valid_nominate_while_inside_entry_subperiod test, we
        # should never get into a state where we have less answers than
        # questions for a form. views/feedback.py:update_feedback uses an
        # atomic transaction to ensure this as well
        answers = [
            FeedbackAnswer(
                id=TEST_FORM_2_ANSWER_1_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=u"Alice",
            ),
            FeedbackAnswer(
                id=TEST_FORM_2_ANSWER_2_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=u"",
            ),
            FeedbackAnswer(
                id=TEST_FORM_2_ANSWER_3_ID,
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=u"Delta",
            ),
        ]
        form.answers = answers
        _dbsession.add(form)


@pytest.fixture
def app_with_nominees_and_existing_feedback_form_inside_entry_subperiod(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = app_with_nominees_inside_entry_subperiod
    _add_test_feedback_forms(get_dbsession(app))
    return app


@pytest.fixture
def app_with_nominees_and_existing_feedback_form_inside_approval_subperiod(
    app_with_nominees_inside_approval_subperiod
):  # noqa: E501
    app = app_with_nominees_inside_approval_subperiod
    _add_test_feedback_forms(get_dbsession(app))
    return app


@pytest.fixture
def app_in_enrollment_subperiod(ldap_mocked_app_with_users):

    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)

    # requires no nominations
    with transaction.manager:
        period = Period(
            id=TEST_PERIOD_ID,
            name=TEST_PERIOD_NAME,
            enrollment_start_utc=days_from_utcnow(-1),
            entry_start_utc=days_from_utcnow(1),
            approval_start_utc=days_from_utcnow(2),
            approval_end_utc=days_from_utcnow(3),
        )
        dbsession.add(period)
    return app


def add_previous_test_summary(dbsession, period_id=TEST_PREVIOUS_PERIOD_ID):
    with transaction.manager:
        summary = FeedbackForm(
            to_username=TEST_EMPLOYEE_2_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=period_id,
            is_summary=True,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=TEST_SUMMARY_ANSWERS[0],
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=TEST_SUMMARY_ANSWERS[1],
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=TEST_SUMMARY_ANSWERS[2],
            ),
        ]
        summary.answers = answers
        dbsession.add(summary)


def add_extra_feedback_histories(dbsession, num):
    period_ids = range(500, 500 + num)
    period_params = zip(period_ids, ["p %s" % p for p in period_ids])
    for p_id, p_name in period_params:
        offset_days = -400 - ((p_id - 490) * 30)
        add_test_period_with_template(
            dbsession,
            Period.ENROLLMENT_SUBPERIOD,
            1,
            period_id=p_id,
            period_name=p_name,
            offset_from_utc_now_days=offset_days,
        )
        add_previous_test_summary(dbsession, p_id)


def set_as_staff(user, ldap_detail):
    user.is_staff = True
    if ldap_detail[ldapauth.DIRECT_REPORTS_KEY]:
        user.has_direct_reports = True
