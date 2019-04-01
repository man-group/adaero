import os.path

from mock import patch
import pytest
import transaction

from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME
)
from feedback_tool.models import FeedbackForm, FeedbackAnswer, Period
from tests.integration.views.conftest import (
    add_test_template,
    add_test_period_with_template,
    get_dbsession,
    successfully_login,
)
from tests.integration.constants import (
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_PREVIOUS_PERIOD_ID,
    TEST_EMPLOYEE_3_USERNAME,
    QUESTION_IDS_AND_TEMPLATES,
    TEST_PREVIOUS_PERIOD_NAME,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_SUMMARY_1,
    TEST_SUMMARY_2,
    TEST_SUMMARY_3,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    TEST_PRODUCTION_HOSTNAME,
    TEST_PRODUCTION_USER,
)
from feedback_tool.constants import (
    EMAIL_TEMPLATE_MAP,
)
from tests.integration.views.test_manager import (
    add_test_data_for_stats,
    TEST_NUM_FORMS_RECEIVED,
    TEST_STATS_NOMINATED_USERS,
)

dirpath = os.path.dirname(__file__)
TEST_CSV_FILEPATH = os.path.join(dirpath, "company_stats.csv")


def test_external_cannot_get_company_feedback_stats_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    response = app.get("/api/v1/company-feedback-stats.csv", expect_errors=True)
    assert response.status_code == 403


def test_employee_cannot_get_company_feedback_stats_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    response = app.get("/api/v1/company-feedback-stats.csv", expect_errors=True)
    assert response.status_code == 403


def test_manager_cannot_get_company_feedback_stats_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_MANAGER_USERNAME
    )
    response = app.get("/api/v1/company-feedback-stats.csv", expect_errors=True)
    assert response.status_code == 403


def test_external_cannot_get_raw_feedback_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    response = app.get("/api/v1/company-raw-feedback.csv", expect_errors=True)
    assert response.status_code == 403


def test_employee_cannot_get_raw_feedback_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    response = app.get("/api/v1/company-raw-feedback.csv", expect_errors=True)
    assert response.status_code == 403


def test_manager_cannot_get_raw_feedback_csv(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_MANAGER_USERNAME
    )
    response = app.get("/api/v1/company-raw-feedback.csv", expect_errors=True)
    assert response.status_code == 403


def test_external_cannot_get_company_feedback_stats(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    response = app.get("/api/v1/company-stats", expect_errors=True)
    assert response.status_code == 403


def test_employee_cannot_get_company_feedback_stats(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_MANAGER_USERNAME
    )
    response = app.get("/api/v1/company-stats", expect_errors=True)
    assert response.status_code == 403


def test_manager_cannot_get_company_feedback_stats(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_MANAGER_USERNAME
    )
    response = app.get("/api/v1/company-stats", expect_errors=True)
    assert response.status_code == 403


def test_talent_manager_can_get_company_feedback_stats_csv(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_TALENT_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    response = app.get("/api/v1/company-feedback-stats.csv")
    assert response.content_type == "text/csv"
    assert response.body == open(TEST_CSV_FILEPATH, "rb").read()


def test_talent_manager_can_get_company_raw_feedback(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_TALENT_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    with transaction.manager:
        form = FeedbackForm(
            to_username=TEST_EMPLOYEE_3_USERNAME,
            from_username=TEST_TALENT_MANAGER_USERNAME,
            period_id=TEST_PREVIOUS_PERIOD_ID,
            is_summary=True,
        )
        answers = [
            FeedbackAnswer(question_id=QUESTION_IDS_AND_TEMPLATES[0][0], content="Foo"),
            FeedbackAnswer(question_id=QUESTION_IDS_AND_TEMPLATES[1][0], content="Bar"),
            FeedbackAnswer(question_id=QUESTION_IDS_AND_TEMPLATES[2][0], content="Tom"),
        ]
        form.answers = answers
        dbsession.add(form)
    response = app.get("/api/v1/company-raw-feedback.csv")
    assert response.content_type == "text/csv"
    num_q = 3
    nominee_1_answers = (
        (7 * num_q) + (3 * num_q) + (2 * num_q) + (TEST_NUM_FORMS_RECEIVED * num_q)
    )
    nominee_2_answers = 2 * num_q
    nominee_3_answers = (3 * num_q) + (8 * num_q) + (10 * num_q) + (2 * num_q)
    summary_answers = 3 * len(TEST_STATS_NOMINATED_USERS)
    num_expected = (
        nominee_1_answers + nominee_2_answers + nominee_3_answers + summary_answers
    )
    # remove csv header and trailing newline
    body = response.body.decode()
    num_generated = len(body.split("\n")) - 2
    assert num_expected == num_generated
    assert body.count(",True,") == summary_answers
    assert (
        body.count(
            "to_username,from_username,is_summary,name," "question_template,content"
        )
        == 1
    )
    raw_answer_row = (
        "{to_username},{from_username},True,{period_name},"
        "{template},{answer}"
        "".format(
            to_username=TEST_EMPLOYEE_3_USERNAME,
            from_username=TEST_TALENT_MANAGER_USERNAME,
            period_name=TEST_PREVIOUS_PERIOD_NAME,
            template=QUESTION_IDS_AND_TEMPLATES[1][1],
            answer="Bar",
        )
    )
    assert body.count(raw_answer_row) == 1


def test_talent_manager_can_correct_summarised_feedback_from_another_manager(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_TALENT_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=Period.REVIEW_SUBPERIOD)
    response = app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_2_USERNAME)
    items = response.json_body["summary"]["items"]
    expected = [
        {"questionId": QUESTION_IDS_AND_TEMPLATES[0][0], "answer": TEST_SUMMARY_1},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[1][0], "answer": TEST_SUMMARY_2},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[2][0], "answer": TEST_SUMMARY_3},
    ]
    generated = sorted(items, key=lambda k: k["questionId"])

    for exp, gen in zip(expected, generated):
        assert exp["questionId"] == gen["questionId"]
        assert exp["answer"] == gen["answer"]


@pytest.mark.parametrize("template_key", tuple(EMAIL_TEMPLATE_MAP.keys()))
def test_talent_manager_can_mass_email(ldap_mocked_app_with_users, template_key):
    with patch("smtplib.SMTP"), patch(
        "socket.gethostname"
    ) as gethostname_mock, patch("getpass.getuser") as getuser_mock:
        gethostname_mock.return_value = TEST_PRODUCTION_HOSTNAME
        getuser_mock.return_value = TEST_PRODUCTION_USER
        app = successfully_login(ldap_mocked_app_with_users, TEST_TALENT_MANAGER_USERNAME)
        dbsession = get_dbsession(app)
        template_id = add_test_template(dbsession)
        add_test_period_with_template(dbsession, Period.ENTRY_SUBPERIOD, template_id)
        csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
        response = app.post_json(
            "/api/v1/send-email", {"templateKey": template_key}, headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        )
        assert response.json_body["success"]

